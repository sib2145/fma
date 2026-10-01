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
                f"{CLI_START_EXTRA_DIALOG_ID} не найден"
            )
            return False

        session.dialog = dialog

    # --------------------------------------------------
    # Processor открытия.
    #
    # Здесь выполняется абсолютно та же логика,
    # что и при открытии диалога в Telegram.
    # --------------------------------------------------

    session = await game.dialogs.on_open_dialog_processor(
        session
    )

    dialog = session.dialog

    if dialog is None:
        print("Текущий диалог отсутствует")
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

    if not dialog.options:
        print("[Нет доступных вариантов]")
    else:
        for index, option in enumerate(
            dialog.options,
            start=1,
        ):
            if index > 99:
                break

            print(
                f"{index}. {option.text.text}"
            )

    print("=" * 60)

    return True


async def choose_cli_option(
    session: DialogSession,
    option_index: int,
):
    dialog = session.dialog

    if dialog is None:
        print("Текущий диалог отсутствует")
        return

    # --------------------------------------------------
    # CLI использует человеческую нумерацию:
    #
    # 1 -> options[0]
    # 2 -> options[1]
    # ...
    # --------------------------------------------------

    index = option_index - 1

    if (
        index < 0
        or index >= len(dialog.options)
    ):
        print(
            f"Нет варианта с номером "
            f"{option_index}"
        )
        return

    option_selected = dialog.options[index]

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
            "после on_close_dialog_processor"
        )
        return

    # --------------------------------------------------
    # CLI пока работает как незарегистрированный
    # пользователь.
    #
    # Поэтому выбор в Player/БД не сохраняем.
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
            "У выбранного варианта "
            "не указан следующий диалог"
        )
        return

    next_dialog = await game.dialogs.get_by_id(
        next_dialog_id
    )

    if next_dialog is None:
        print(
            f"Диалог {next_dialog_id} не найден"
        )
        return

    # --------------------------------------------------
    # Устанавливаем следующий диалог
    # непосредственно в CLI-сессию.
    # --------------------------------------------------

    session.dialog = next_dialog

    # --------------------------------------------------
    # Сразу показываем его.
    # --------------------------------------------------

    await show_cli_dialog(session)








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

        await show_cli_dialog(session)

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
            print("Остановка программы...")
            break

        command, args = parse_command(
            input_line
        )

        # --------------------------------------------------
        # Число в режиме --cli означает выбор
        # соответствующей опции текущего диалога.
        #
        # Например:
        #
        #   1
        #   2
        #   3
        #
        # В обычном режиме без --cli числа пока
        # не имеют специального значения.
        # --------------------------------------------------

        if cli and isinstance(command, int):
            if 1 <= command <= 99:
                await choose_cli_option(
                    session,
                    command
                )
            else:
                print(
                    "Номер варианта должен быть "
                    "от 1 до 99."
                )

            continue

        # --------------------------------------------------
        # Команда cli включает игровой интерфейс.
        #
        # Если он ещё не был включён, создаём игровую
        # сессию и показываем стартовый диалог.
        #
        # Если cli уже активен, просто обновляем
        # текущий диалог.
        # --------------------------------------------------

        if command == "cli":
            if not cli:
                cli = True
                session = DialogSession()

                await show_cli_dialog(
                    session
                )
            else:
                await show_cli_dialog(
                    session
                )

            continue

        # --------------------------------------------------
        # Системные команды консоли.
        # --------------------------------------------------

        if command == "help":
            print()
            print("Доступные команды:")
            print("  help   - показать список команд")
            print("  status - показать состояние игры")
            print(
                "  cli    - показать игровой диалог"
            )
            print(
                "  Enter  - остановить программу"
            )
            print()

        elif command == "status":
            print()
            print("Сервер запущен.")

            if cli and session is not None:
                if session.dialog is not None:
                    print(
                        f"Текущий диалог: "
                        f"{session.dialog.id}"
                    )
                else:
                    print(
                        "Текущий диалог: отсутствует"
                    )

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
    # --------------------------------------------------

    game_task = asyncio.create_task(
        game.run()
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
        )
    )

    tasks = [
        game_task,
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
            dp.start_polling(bot)
        )

        tasks.append(telegram_task)

    try:
        # --------------------------------------------------
        # Ждём завершения любой из основных задач.
        #
        # Например:
        #   - пользователь нажал Enter в консоли;
        #   - остановилась игра;
        #   - Telegram polling завершился.
        #
        # Остальные задачи пока продолжают работать.
        # --------------------------------------------------

        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED
        )

    finally:
        # --------------------------------------------------
        # Останавливаем все оставшиеся задачи.
        # --------------------------------------------------

        for task in tasks:
            if not task.done():
                task.cancel()

        # --------------------------------------------------
        # Дожидаемся завершения отменённых задач.
        # --------------------------------------------------

        await asyncio.gather(
            *tasks,
            return_exceptions=True
        )

        # --------------------------------------------------
        # Останавливаем игровую систему.
        # --------------------------------------------------

        await game.stop()


if __name__ == "__main__":
    asyncio.run(main())