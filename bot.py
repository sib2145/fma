import asyncio

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import configparser

from textwrap import dedent #Убирает отступы в тексте

from handlers.welcome import welcome_router
from handlers.dialog import dialog_router
from handlers.admin import admin_router
from handlers.basic_handlers import router

from instances.game import game
from instances.db import db

def load_config():
    config = configparser.ConfigParser()
    config.read("config.ini")

    return config

config = load_config()

TOKEN = config["telegram"]["token"]

bot = Bot(token=TOKEN)
dp = Dispatcher()


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


async def console():
    while True:
        input_line = await asyncio.to_thread(input, "")

        command, args = parse_command(input_line)

        if command == "":
            print("Остановка программы...")
            await dp.stop_polling()
            return

        if command == "help":
            print("help   - список команд")
            print("status - состояние игры")
            print("Enter  - остановить программу")
            
        elif command == "t":
            print("Тестовая команда")

            try:
                dialog = await game.dialogs.get_by_id(1)
                print(dialog.id)
            except Exception as e:
                print(f"Ошибка: {type(e).__name__}: {e}")

        elif command == "status":
            print("Игра работает")
            
        elif command == "player":

            if len(args) == 0:
                print(dedent("""
        Команды player:

        player register <telegram_id> [locale_id]
            - зарегистрировать игрока

        player delete <id>
            - удалить игрока

        player dialog <player_id> [dialog_id]
            - установить текущий диалог игрока

        Если dialog_id не указан, текущий диалог будет сброшен.

        Примеры:

        player register 123456789
        player register 123456789 2
        player delete 15
        player dialog 15 42
        player dialog 15
        """))
                continue

            subcommand = args[0]

            if subcommand == "register":

                if len(args) < 2:
                    print("Использование: player register <telegram_id> [locale_id]")
                    continue

                telegram_id = args[1]

                if not isinstance(telegram_id, int):
                    print("telegram_id должен быть числом")
                    continue

                if len(args) >= 3:
                    locale_id = args[2]

                    if not isinstance(locale_id, int):
                        print("locale_id должен быть числом")
                        continue

                    player = await game.players.register(
                        telegram_id,
                        locale_id
                    )
                else:
                    # locale_id не указан.
                    # Используется значение по умолчанию из register()
                    player = await game.players.register(
                        telegram_id
                    )

                print(f"Игрок зарегистрирован: {player}")
                
            elif subcommand == "delete":

                if len(args) < 2:
                    print("Использование: player delete <id>")
                    continue

                player_id = args[1]

                if not isinstance(player_id, int):
                    print("id игрока должен быть числом")
                    continue

                deleted = await game.players.delete(player_id)

                if deleted:
                    print(f"Игрок с id {player_id} удалён")
                else:
                    print(f"Игрок с id {player_id} не найден")
                    
            elif subcommand == "dialog":

                if len(args) < 2:
                    print("Использование: player dialog <player_id> [dialog_id]")
                    continue

                player_id = args[1]

                if not isinstance(player_id, int):
                    print("player_id должен быть числом")
                    continue

                if len(args) >= 3:
                    dialog_id = args[2]

                    if not isinstance(dialog_id, int):
                        print("dialog_id должен быть числом")
                        continue
                else:
                    dialog_id = None

                updated = await game.players.set_current_dialog(
                    player_id,
                    dialog_id
                )

                if not updated:
                    print(f"Игрок с id {player_id} не найден")
                    continue

                if dialog_id is None:
                    print(f"Текущий диалог игрока {player_id} сброшен")
                else:
                    print(
                        f"Игроку {player_id} установлен "
                        f"текущий диалог {dialog_id}"
                    )

            else:
                print(f"Неизвестная команда player: {subcommand}")


        else:
            print(f"Неизвестная команда: {command}")


async def main():
    game_task = asyncio.create_task(game.run())
    console_task = asyncio.create_task(console())

    try:
        dp.include_router(welcome_router)
        dp.include_router(dialog_router)
        dp.include_router(admin_router)
        dp.include_router(router)

        await bot.delete_webhook(drop_pending_updates=True)

        await dp.start_polling(bot)

    finally:
        console_task.cancel()

        await game.stop()
        await game_task


if __name__ == "__main__":
    asyncio.run(main())