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
    input_line: str,
):
    dialog = session.dialog

    if dialog is None:
        print("Текущий диалог отсутствует.")
        return

    # --------------------------------------------------
    # Если диалог ожидает пользовательский ввод,
    # любая непустая строка передаётся в processor.
    #
    # Важно: здесь строка НЕ разбирается как команда
    # консоли или как выбор игровой опции.
    # --------------------------------------------------

    if dialog.input_type == 1:
        await process_cli_value(
            session,
            input_line,
        )

        return

    # --------------------------------------------------
    # Если диалог не ожидает пользовательский ввод,
    # выбор игровой опции осуществляется только через
    # конструкцию:
    #
    #   =1
    #   =2
    #   =3
    #
    # Обычное число вроде "1" не является выбором.
    # --------------------------------------------------

    if input_line.startswith("="):
        value = input_line[1:]

        try:
            option_number = int(value)
        except ValueError:
            print(
                "Неверный номер варианта. "
                "Используйте, например: =1"
            )
            return

        if not 1 <= option_number <= 99:
            print(
                "Номер варианта должен быть "
                "от 1 до 99."
            )
            return

        await choose_cli_option(
            session,
            option_number,
        )

        return

    # --------------------------------------------------
    # Всё остальное передаём как команду консоли.
    # --------------------------------------------------

    command, args = parse_command(
        input_line
    )

    if command == "help":
        print()
        print("Доступные команды:")
        print("  help   - показать список команд")
        print("  status - показать состояние игры")
        print("  cli    - показать игровой диалог")
        print("  =1-99  - выбрать вариант диалога")
        print("  Enter  - остановить программу")
        print()

    elif command == "status":
        print()
        print("Сервер запущен.")

        if session.dialog is not None:
            print(
                f"Текущий диалог: "
                f"{session.dialog.id}"
            )

        print()

    elif command == "cli":
        await show_cli_dialog(
            session
        )

    else:
        print(
            f"Неизвестная команда: {command}"
        )

async def process_cli_value(
    session: DialogSession,
    value: str,
):
    # --------------------------------------------------
    # Запоминаем диалог, из которого был выполнен ввод.
    #
    # Если ввод окажется некорректным, processor вернёт
    # valid=False, и мы должны остаться на этом же диалоге.
    # --------------------------------------------------

    input_dialog = session.dialog

    if input_dialog is None:
        print(
            "Текущий диалог отсутствует."
        )
        return

    input_dialog_id = input_dialog.id

    # --------------------------------------------------
    # Сохраняем пользовательский ввод в session.
    #
    # ВАЖНО:
    # on_input_dialog_processor() читает именно
    # session.user_input, а не processor_data.
    #
    # Это тот же контракт, который используется
    # Telegram handler.
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
    # Если processor вернул сообщение об ошибке,
    # выводим его в консоль.
    # --------------------------------------------------

    if error_message is not None:
        print()
        print(
            f"Ошибка: {error_message}"
        )
        print()

    # --------------------------------------------------
    # Если ввод некорректный, возвращаемся
    # к исходному диалогу.
    # --------------------------------------------------

    if not valid:
        dialog = await game.dialogs.get_by_id(
            input_dialog_id
        )

        if dialog is None:
            print(
                f"Не удалось вернуть диалог "
                f"{input_dialog_id}."
            )
            return

        session.dialog = dialog

    # --------------------------------------------------
    # Если valid=True, используем session,
    # которую вернул processor.
    #
    # Processor мог изменить:
    #
    #   - dialog
    #   - processor_data
    #   - user_input
    #   - и т.д.
    # --------------------------------------------------

    await show_cli_dialog(
        session
    )



async def choose_cli_option(
    session: DialogSession,
    option_number: int,
):
    dialog = session.dialog

    if dialog is None:
        print(
            "Текущий диалог отсутствует."
        )
        return

    # --------------------------------------------------
    # CLI использует человеческую нумерацию:
    #
    #   =1 -> options[0]
    #   =2 -> options[1]
    #   =3 -> options[2]
    # --------------------------------------------------

    index = option_number - 1

    if (
        index < 0
        or index >= len(dialog.options)
    ):
        print(
            f"Нет варианта с номером "
            f"{option_number}."
        )
        return

    option_selected = dialog.options[index]

    print(
        f"Выбран вариант: "
        f"{option_number} "
        f"({option_selected.text.text})"
    )

    # --------------------------------------------------
    # Передаём выбранную кнопку в session.
    # --------------------------------------------------

    session.processor_data[
        "selected_option"
    ] = option_selected

    # --------------------------------------------------
    # Processor закрытия.
    # --------------------------------------------------

    session = await game.dialogs.on_close_dialog_processor(
        session
    )

    option_selected = session.processor_data.get(
        "selected_option"
    )

    if option_selected is None:
        print(
            "selected_option отсутствует "
            "после on_close_dialog_processor."
        )
        return

    # --------------------------------------------------
    # CLI пока работает без зарегистрированного
    # игрока, поэтому сохранение выбора в БД
    # не выполняем.
    # --------------------------------------------------

    next_dialog_id = (
        option_selected.next_dialog_id
    )

    if next_dialog_id is None:
        next_dialog_id = (
            dialog.next_dialog_id
        )

    if next_dialog_id is None:
        print(
            "Следующий диалог не указан."
        )
        return

    next_dialog = await game.dialogs.get_by_id(
        next_dialog_id
    )

    if next_dialog is None:
        print(
            f"Диалог {next_dialog_id} "
            f"не найден."
        )
        return

    # --------------------------------------------------
    # Устанавливаем следующий диалог.
    # --------------------------------------------------

    session.dialog = next_dialog

    # --------------------------------------------------
    # Показываем новый диалог.
    # --------------------------------------------------

    await show_cli_dialog(
        session
    )
    

async def show_cli_dialog(
    session: DialogSession,
):
    # --------------------------------------------------
    # Если в session нет диалога, начинаем со
    # стартового extra-диалога.
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
    # --------------------------------------------------

    session = await game.dialogs.on_open_dialog_processor(
        session
    )

    dialog = session.dialog

    if dialog is None:
        print(
            "Текущий диалог отсутствует."
        )
        return False

    # --------------------------------------------------
    # Рендерим текст и динамические кнопки.
    # --------------------------------------------------

    dialog = await game.dialogs.render_view(
        dialog
    )

    session.dialog = dialog

    # --------------------------------------------------
    # Выводим диалог.
    # --------------------------------------------------

    print()
    print("=" * 60)
    print(
        f"Диалог #{dialog.id}"
    )
    print("=" * 60)

    print(dialog.text.text)

    print()

    # --------------------------------------------------
    # input_type == 1 означает, что диалог ожидает
    # пользовательский ввод.
    # --------------------------------------------------

    if dialog.input_type == 1:
        print(
            "[Ожидается ввод]"
        )

    elif not dialog.options:
        print(
            "[Нет доступных вариантов]"
        )

    else:
        for index, option in enumerate(
            dialog.options,
            start=1,
        ):
            if index > 99:
                break

            print(
                f"={index}. {option.text.text}"
            )

    print("=" * 60)

    return True



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
