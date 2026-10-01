import asyncio

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from textwrap import dedent #Убирает отступы в тексте

from handlers.welcome import welcome_router
from handlers.dialog import dialog_router
from handlers.admin import admin_router
from handlers.basic_handlers import router

from instances.game import game
from instances.db import db

from config import config

import argparse

from config import config, CLI_START_EXTRA_DIALOG_ID
from views.dialog_session import DialogSession

cli_session = DialogSession()

cli_note_text = dedent("""
CLI  мод позволяет использовать единые диалоги на движке игры для игры или админки из консоли.

Пункты диалогов выбираются вводом номера опции. Например, ввод =1 в консоль там, где предполагается выбор опций, выберет первую опцию. Все опции подписаны.
При этом консольные команды сервера вроде help все еще работают

В тех диалогах, где предполагается пользовательский ввод, можно вводить в консоли просто обычный текст, который должен быть введен. 
Этот ввод имеет приоритет над консольными командами сервера.
""")

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Запустить Telegram-бота",
        #default=True
    )

    parser.add_argument(
        "--cli",
        action="store_true",
        help="Запустить консольный интерфейс",
        #default=True
    )

    return parser.parse_args()
    
async def process_cli_input(
    session: DialogSession,
    value: str,
):
    # --------------------------------------------------
    # Пустой ввод ничего не делает.
    # --------------------------------------------------

    if not value:
        return

    # --------------------------------------------------
    # Ввод вида =N используется для выбора опции.
    #
    # Это имеет приоритет над input_type.
    # Поэтому даже диалог, ожидающий пользовательский
    # текст, может иметь кнопки.
    # --------------------------------------------------

    if value.startswith("="):
        option_number = value[1:]

        if not option_number.isdigit():
            print(
                "Выбор опции должен иметь формат =N."
            )
            return

        option_number = int(option_number)

        await choose_cli_dialog_option(
            session,
            option_number,
        )

        return

    # --------------------------------------------------
    # Если текущий диалог ожидает пользовательский
    # ввод, передаём строку в input processor.
    # --------------------------------------------------

    if (
        session.dialog is not None
        and session.dialog.input_type == 1
    ):
        await process_cli_value(
            session,
            value,
        )

        return

    # --------------------------------------------------
    # Обычный текст в диалоге, который не ожидает
    # пользовательский ввод, ничего не делает.
    # --------------------------------------------------

    print(
        "Этот диалог не ожидает текстовый ввод."
    )



async def process_cli_value(
    session: DialogSession,
    value: str,
):
    # --------------------------------------------------
    # Запоминаем текущий диалог.
    #
    # Если ввод окажется некорректным, остаёмся
    # на этом же диалоге.
    #
    # Если ввод корректный, после processor'а
    # переходим на его next_dialog_id.
    # --------------------------------------------------

    dialog = session.dialog

    if dialog is None:
        print(
            "Текущий диалог отсутствует."
        )
        return

    current_dialog_id = dialog.id

    # --------------------------------------------------
    # Сохраняем пользовательский ввод в session.
    #
    # on_input_dialog_processor() использует
    # именно session.user_input.
    # --------------------------------------------------

    session.user_input = value

    # --------------------------------------------------
    # Processor пользовательского ввода.
    #
    # Возвращает:
    #
    #   valid
    #   изменённую session
    #   error_message
    # --------------------------------------------------

    (
        valid,
        session,
        error_message,
    ) = await game.dialogs.on_input_dialog_processor(
        session
    )

    # --------------------------------------------------
    # Выводим сообщение об ошибке, если processor
    # его сформировал.
    # --------------------------------------------------

    if error_message is not None:
        print()
        print(
            f"Ошибка: {error_message}"
        )
        print()

    # --------------------------------------------------
    # Некорректный ввод.
    #
    # Остаёмся на том же диалоге и просто показываем
    # его снова.
    # --------------------------------------------------

    if not valid:
        dialog = await game.dialogs.get_by_id(
            current_dialog_id
        )

        if dialog is None:
            print(
                f"Не удалось вернуть диалог "
                f"{current_dialog_id}."
            )
            return

        session.dialog = dialog

        await show_cli_dialog(
            session
        )

        return

    # --------------------------------------------------
    # Корректный ввод.
    #
    # on_input_dialog_processor() мог изменить
    # processor_data, например:
    #
    #   viewing_dialog = DialogView(id=1, ...)
    #
    # Но session.dialog при этом остаётся текущим
    # диалогом ввода (например, диалогом 9).
    #
    # Как и в Telegram, теперь переходим на
    # next_dialog_id текущего диалога.
    # --------------------------------------------------

    dialog = session.dialog

    if (
        dialog is None
        or dialog.next_dialog_id is None
    ):
        print(
            "После пользовательского ввода "
            "следующий диалог не установлен."
        )

        await show_cli_dialog(
            session
        )

        return

    # --------------------------------------------------
    # Загружаем следующий диалог.
    #
    # Для нашего примера:
    #
    #   9 -> 6
    #
    # При этом processor_data сохраняется,
    # поэтому диалог 6 получит:
    #
    #   viewing_dialog = диалог 1
    #
    # и его on_open processor сможет показать
    # данные просмотренного диалога.
    # --------------------------------------------------

    next_dialog = await game.dialogs.get_by_id(
        dialog.next_dialog_id
    )

    if next_dialog is None:
        print(
            f"Следующий диалог "
            f"{dialog.next_dialog_id} не найден."
        )
        return

    session.dialog = next_dialog

    # --------------------------------------------------
    # Показываем новый текущий диалог.
    #
    # show_cli_dialog() вызовет on_open processor,
    # поэтому для диалога 6 будет обработан
    # processor_data["viewing_dialog"].
    # --------------------------------------------------

    await show_cli_dialog(
        session
    )

async def show_cli_dialog(session):
    # --------------------------------------------------
    # Если текущий диалог отсутствует, устанавливаем
    # стартовый extra-диалог для CLI.
    # --------------------------------------------------

    if session.dialog is None:
        dialog = await game.dialogs.get_by_id(
            CLI_START_EXTRA_DIALOG_ID
        )

        if dialog is None:
            print(
                f"Стартовый диалог "
                f"{CLI_START_EXTRA_DIALOG_ID} не найден."
            )
            return False

        session.dialog = dialog

    # --------------------------------------------------
    # Processor открытия.
    #
    # Здесь выполняется вся динамическая подготовка
    # диалога.
    #
    # Например, для диалога #6:
    #
    #   processor_data["viewing_dialog"]
    #       ↓
    #   dialog.template_context["dialog"]
    #
    # При этом session.dialog остаётся диалогом #6.
    # --------------------------------------------------

    session = await game.dialogs.on_open_dialog_processor(
        session
    )

    # --------------------------------------------------
    # Берём изменённый DialogView из session.
    # --------------------------------------------------

    dialog = session.dialog

    if dialog is None:
        print(
            "Текущий диалог отсутствует."
        )
        return False

    # --------------------------------------------------
    # Рендерим DialogView.
    #
    # Это тот же самый этап, который выполняется
    # в Telegram handler.
    #
    # render_view() использует template_context,
    # сформированный processor'ом.
    #
    # Поэтому для диалога #6:
    #
    #   dialog.id == 6
    #
    # но:
    #
    #   dialog.template_context["dialog"].id == 21
    #
    # и в текст шаблона #6 будут подставлены
    # данные просматриваемого диалога #21.
    # --------------------------------------------------

    dialog = await game.dialogs.render_view(
        dialog
    )

    # --------------------------------------------------
    # Сохраняем отрендеренный DialogView в session.
    #
    # Это соответствует Telegram handler.
    # --------------------------------------------------

    session.dialog = dialog

    # --------------------------------------------------
    # Отображение.
    # --------------------------------------------------

    print()
    print("=" * 60)

    print(
        f"Диалог #{dialog.id}"
    )

    print("=" * 60)

    # --------------------------------------------------
    # Показываем уже отрендеренный текст.
    # --------------------------------------------------

    if dialog.text is not None:
        print(
            dialog.text.text
        )

    # --------------------------------------------------
    # input_type и options независимы друг от друга.
    #
    # Диалог может одновременно:
    #
    #   - принимать текст;
    #   - иметь кнопки.
    # --------------------------------------------------

    if dialog.input_type == 1:
        print()
        print(
            "[Ожидается ввод]"
        )

    # --------------------------------------------------
    # Показываем кнопки независимо от input_type.
    #
    # Для CLI выбор выполняется через:
    #
    #   =1
    #   =2
    #   =3
    # --------------------------------------------------

    if dialog.options:
        print()

        for index, option in enumerate(
            dialog.options,
            start=1,
        ):
            print(
                f"={index}. {option.text.text}"
            )

    print("=" * 60)

    return True


async def choose_cli_dialog_option(
    session,
    option_number: int,
):
    dialog = session.dialog

    if dialog is None:
        print(
            "Текущий диалог отсутствует."
        )
        return

    # --------------------------------------------------
    # Получаем доступные опции текущего диалога.
    # --------------------------------------------------

    options = dialog.options

    if (
        option_number < 1
        or option_number > len(options)
    ):
        print(
            f"Опция {option_number} не существует."
        )
        return

    option = options[option_number - 1]

    print(
        f"Выбран вариант: "
        f"{option_number} "
        f"({option.text.text})"
    )

    # --------------------------------------------------
    # Сохраняем выбранную опцию в processor_data.
    #
    # Это тот же механизм, который используется
    # Telegram handler.
    #
    # on_close_dialog_processor() получает выбранную
    # опцию отсюда.
    # --------------------------------------------------

    session.processor_data["selected_option"] = option

    # --------------------------------------------------
    # Processor закрытия текущего диалога.
    #
    # Он может изменить session, например:
    #
    #   - изменить processor_data;
    #   - изменить dialog;
    #   - обработать processor_flag;
    #   - изменить выбранную опцию.
    # --------------------------------------------------

    session = await game.dialogs.on_close_dialog_processor(
        session
    )

    # --------------------------------------------------
    # Получаем выбранную опцию после processor.
    #
    # Processor может изменить её или удалить.
    # --------------------------------------------------

    option = session.processor_data.get(
        "selected_option"
    )

    if option is None:
        print(
            "После обработки диалога "
            "выбранная опция отсутствует."
        )
        return

    # --------------------------------------------------
    # Если processor уже изменил текущий диалог,
    # не перезаписываем его обычным переходом.
    #
    # Это важно для специальных processor'ов.
    # --------------------------------------------------

    if session.dialog is not dialog:
        await show_cli_dialog(
            session
        )
        return

    # --------------------------------------------------
    # Если следующего диалога нет, остаёмся
    # без перехода.
    # --------------------------------------------------

    if option.next_dialog_id is None:
        print(
            "У выбранной опции "
            "не указан следующий диалог."
        )
        return

    # --------------------------------------------------
    # Загружаем следующий диалог.
    # --------------------------------------------------

    next_dialog = await game.dialogs.get_by_id(
        option.next_dialog_id
    )

    if next_dialog is None:
        print(
            f"Следующий диалог "
            f"{option.next_dialog_id} не найден."
        )
        return

    # --------------------------------------------------
    # Переходим на следующий диалог.
    # --------------------------------------------------

    session.dialog = next_dialog

    # --------------------------------------------------
    # Отображаем его.
    #
    # show_cli_dialog() вызовет on_open processor
    # и выполнит render_view().
    # --------------------------------------------------

    await show_cli_dialog(
        session
    )

    




def parse_command(input_line: str):
    input_line = input_line.strip()

    if not input_line:
        return "", []

    parts = []
    current = []
    in_quotes = False
    was_quoted = False

    i = 0

    while i < len(input_line):
        char = input_line[i]

        if char == '"':
            # Экранированная кавычка: ""
            if in_quotes and i + 1 < len(input_line) and input_line[i + 1] == '"':
                current.append('"')
                i += 2
                continue

            in_quotes = not in_quotes
            was_quoted = True

            i += 1
            continue

        if char.isspace() and not in_quotes:
            if current or was_quoted:
                value = "".join(current)

                if not was_quoted:
                    if value.isdigit() or (
                        value.startswith("-") and value[1:].isdigit()
                    ):
                        value = int(value)

                parts.append(value)

                current = []
                was_quoted = False

            i += 1
            continue

        current.append(char)
        i += 1

    if current or was_quoted:
        value = "".join(current)

        if not was_quoted:
            if value.isdigit() or (
                value.startswith("-") and value[1:].isdigit()
            ):
                value = int(value)

        parts.append(value)

    if not parts:
        return "", []

    command = parts[0]
    args = parts[1:]

    return command, args


async def console(cli: bool = False):
    # --------------------------------------------------
    # Игровая CLI-сессия создаётся только при наличии
    # флага --cli.
    #
    # Обычная серверная консоль работает всегда.
    # --------------------------------------------------

    session = None

    if cli:
        session = DialogSession()
        
        print(cli_note_text)

        # --------------------------------------------------
        # Если игровой CLI включён при запуске, сразу
        # показываем текущий диалог.
        # --------------------------------------------------

        if not await show_cli_dialog(session):
            print(
                "CLI-режим не может быть запущен (show_cli_dialog не вернула true)"
            )

    while True:
        try:
            input_line = await asyncio.to_thread(
                input,
                "> "
            )

        except (EOFError, KeyboardInterrupt):
            print()
            break

        # --------------------------------------------------
        # Пустой ввод — команда остановки программы.
        # --------------------------------------------------

        if not input_line.strip():
            print(
                "Остановка программы..."
            )
            break

        # --------------------------------------------------
        # Если игровой CLI ещё не включён, команда cli
        # запускает его прямо во время работы программы.
        # --------------------------------------------------

        if (
            not cli
            and input_line.strip() == "cli"
        ):
            cli = True
            session = DialogSession()

            print(cli_note_text)

            await show_cli_dialog(
                session
            )

            continue

        # --------------------------------------------------
        # Если CLI активен, передаём ввод игровому
        # маршрутизатору.
        #
        # Он сам определит:
        #
        #   =1     -> выбор опции
        #   любой
        #   текст  -> пользовательский ввод,
        #              если input_type == 1
        #   help   -> команда консоли
        #   status -> команда консоли
        #   cli    -> обновление диалога
        # --------------------------------------------------

        if cli:
            await process_cli_input(
                session,
                input_line,
            )

            continue

        # --------------------------------------------------
        # Обычная серверная консоль.
        # --------------------------------------------------

        command, args = parse_command(
            input_line
        )

        if command == "help":
            print()
            print("Доступные команды:")
            print(
                "  help   - показать список команд"
            )
            print(
                "  status - показать состояние игры"
            )
            print(
                "  cli    - включить игровой CLI"
            )
            print(
                "  Enter  - остановить программу"
            )
            print()

        elif command == "status":
            print()
            print("Сервер запущен.")
            print()

        else:
            print(
                f"Неизвестная команда: {command}"
            )




async def main():
    args = parse_args()

    print(
        "Starting server with arguments: ",
        vars(args)
    )

    # --------------------------------------------------
    # Запускаем игровую систему.
    #
    # Игровой движок работает в фоне и не определяет
    # жизненный цикл приложения.
    # --------------------------------------------------

    game_task = asyncio.create_task(
        game.run(),
        name="game"
    )

    # --------------------------------------------------
    # Telegram является опциональным интерфейсом.
    # --------------------------------------------------

    if args.telegram:
        TOKEN = config["telegram"]["token"]

        bot = Bot(token=TOKEN)
        dp = Dispatcher()

        dp.include_router(welcome_router)
        dp.include_router(dialog_router)
        dp.include_router(admin_router)
        dp.include_router(router)

        await bot.delete_webhook(
            drop_pending_updates=True
        )

    # --------------------------------------------------
    # Консоль сервера работает всегда.
    #
    # Параметр cli только включает дополнительный
    # игровой интерфейс внутри консоли.
    # --------------------------------------------------

    console_task = asyncio.create_task(
        console(
            cli=args.cli
        ),
        name="console"
    )

    # --------------------------------------------------
    # В tasks находятся интерфейсы приложения.
    #
    # game_task намеренно здесь отсутствует:
    # игровой движок работает в фоне и не должен
    # самостоятельно завершать приложение.
    # --------------------------------------------------

    tasks = [
        console_task,
    ]

    # --------------------------------------------------
    # Telegram запускается как ещё одна задача.
    #
    # Благодаря этому в будущем сюда можно будет
    # добавлять другие интерфейсы:
    #
    #   - web
    #   - websocket
    #   - discord
    #   - и т.д.
    #
    # При этом main() не будет зависеть от конкретного
    # способа взаимодействия с игрой.
    # --------------------------------------------------

    if args.telegram:
        telegram_task = asyncio.create_task(
            dp.start_polling(bot),
            name="telegram"
        )

        tasks.append(telegram_task)

    try:
        # --------------------------------------------------
        # Ждём завершения любого интерфейса.
        #
        # Например:
        #   - пользователь нажал Enter в консоли;
        #   - Telegram polling завершился;
        #   - в будущем завершился web-интерфейс.
        #
        # Игровой движок здесь не участвует:
        # он работает в фоне всё время жизни приложения.
        # --------------------------------------------------

        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED
        )

        # --------------------------------------------------
        # Временно выводим информацию о завершившейся
        # задаче.
        #
        # Это поможет понять, почему приложение
        # завершилось само.
        # --------------------------------------------------

        for task in done:
            print(
                "Завершилась задача:",
                task.get_name()
            )

            if task.cancelled():
                print(
                    "Задача была отменена."
                )

            elif task.exception() is not None:
                print(
                    "Задача завершилась с ошибкой:"
                )
                print(
                    repr(task.exception())
                )

                # --------------------------------------------------
                # Не скрываем исключение.
                #
                # Пока отлаживаем запуск CLI, лучше сразу увидеть
                # реальную ошибку.
                # --------------------------------------------------

                raise task.exception()

    finally:
        # --------------------------------------------------
        # Останавливаем интерфейсы.
        # --------------------------------------------------

        for task in tasks:
            if not task.done():
                task.cancel()

        # --------------------------------------------------
        # Дожидаемся завершения интерфейсов.
        #
        # Исключения здесь уже не скрываем для завершившихся
        # задач, потому что выше мы их проверили.
        # --------------------------------------------------

        await asyncio.gather(
            *tasks,
            return_exceptions=True
        )

        # --------------------------------------------------
        # Останавливаем игровую систему.
        # --------------------------------------------------

        await game.stop()

        # --------------------------------------------------
        # Дожидаемся завершения игрового движка.
        # --------------------------------------------------

        await asyncio.gather(
            game_task,
            return_exceptions=True
        )


if __name__ == "__main__":
    asyncio.run(main())
