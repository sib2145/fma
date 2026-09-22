import asyncio

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import configparser

from handlers.basic_handlers import router

from instances import game

def load_config():
    config = configparser.ConfigParser()
    config.read("config.ini")

    return config

config = load_config()

TOKEN = config["telegram"]["token"]

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def main():
    game_task = asyncio.create_task(game.run())

    try:
        dp.include_router(router)
        
        await bot.delete_webhook(drop_pending_updates=True) # Удалить старые сообщения, пока бот был оффлайн
        await dp.start_polling(bot)
    finally:
        game.stop()
        await game_task


if __name__ == "__main__":
    asyncio.run(main())
