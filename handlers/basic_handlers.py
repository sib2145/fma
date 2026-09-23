from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import configparser

from instances import game

config = configparser.ConfigParser()
config.read("config.ini")

allowed_users = config["access"].get("allowed_users", "")
ALLOWED_USERS = {
    int(user_id.strip())
    for user_id in allowed_users.split(",")
    if user_id.strip()
}

router = Router()

# Обработчик для остальных сообщений    
@router.message(F.text)
async def echo_handler(message: Message):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer(f"You don't have access to this bot. Your telegram id is: {message.from_user.id}")
        return
        
    await message.answer(f"Я получил твое сообщение. Ты написал: {message.text}")


@router.callback_query()
async def handle_callback(callback: CallbackQuery):
    if callback.from_user.id not in ALLOWED_USERS:
        await callback.message.answer(f"You don't have access to this bot. Your telegram id is: {callback.message.from_user.id}")
        return

    await callback.answer()

    await callback.message.answer(f"Незарегистрированный callback: {callback.data}")