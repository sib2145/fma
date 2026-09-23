import asyncio

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import configparser

from handlers.welcome import welcome_router
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


async def console():
    while True:
        command = await asyncio.to_thread(input, "")

        if command == "":
            print("Остановка программы...")
            await dp.stop_polling()
            return

        if command == "help":
            print("help   - список команд")
            print("status - состояние игры")
            print("Enter  - остановить программу")

        elif command == "status":
            print("Игра работает")

        else:
            print(f"Неизвестная команда: {command}")


async def main():
    game_task = asyncio.create_task(game.run())
    console_task = asyncio.create_task(console())

    try:
        dp.include_router(welcome_router)
        dp.include_router(router)

        await bot.delete_webhook(drop_pending_updates=True)

        await dp.start_polling(bot)

    finally:
        console_task.cancel()

        await game.stop()
        await game_task


if __name__ == "__main__":
    asyncio.run(main())