from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import configparser

from instances.game import game
from instances.db import db

config = configparser.ConfigParser()
config.read("config.ini")

allowed_users = config["access"].get("allowed_users", "")
ALLOWED_USERS = {
    int(user_id.strip())
    for user_id in allowed_users.split(",")
    if user_id.strip()
}

welcome_router = Router()

# Главное меню
async def start_menu(message: Message, edit = False):
    
    text = await db.GetLocaleText(5000)
    
    builder = InlineKeyboardBuilder()
    
    builder.button(text = await db.GetLocaleText(1), callback_data = "welcome:how_interest") # Что интересного
    builder.button(text = await db.GetLocaleText(2), callback_data = "welcome:create_account_rules_short") # Создать аккаунт - краткие правила
    builder.button(text = await db.GetLocaleText(3), callback_data = "welcome:rating") # Рейтинг игроков
    builder.button(text = await db.GetLocaleText(4), callback_data = "welcome:world_stat") # Статистика по миру
    
    builder.adjust(1)
    
    if edit:
        await message.edit_text(
            text,
            reply_markup = builder.as_markup(),
            parse_mode = "HTML"
        )
    else:
        await message.answer(
            text,
            reply_markup = builder.as_markup(),
            parse_mode = "HTML"
        )

# Открытие главного меню при /start
@welcome_router.message(CommandStart())
async def start(message: Message):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer(f"You don't have access to this bot. Your telegram id is: {message.from_user.id}")
        return
    await start_menu(message)

# Открытие главного меню маршрутом    
@welcome_router.callback_query(F.data=="welcome:main")
async def main(callback: CallbackQuery):
    await callback.answer()
    await start_menu(callback.message, True)

# Что интересного    
@welcome_router.callback_query(F.data=="welcome:how_interest")
async def how_interest(callback: CallbackQuery):
    await callback.answer()
    
    text = await db.GetLocaleText(5001)
    
    builder = InlineKeyboardBuilder()
    
    builder.button(text = await db.GetLocaleText(2), callback_data = "welcome:create_account_rules_short") # Создать аккаунт - краткие правила
    builder.button(text = await db.GetLocaleText(3), callback_data = "welcome:rating") # Рейтинг игроков
    builder.button(text = await db.GetLocaleText(4), callback_data = "welcome:world_stat") # Статистика по миру
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        text,
        reply_markup = builder.as_markup(),
        parse_mode = "HTML"
    )

# Создать аккаунт - краткие правила    
@welcome_router.callback_query(F.data=="welcome:create_account_rules_short")
async def create_account_rules_short(callback: CallbackQuery):
    await callback.answer()
    
    text = await db.GetLocaleText(5002)
    
    builder = InlineKeyboardBuilder()
    
    builder.button(text = await db.GetLocaleText(5), callback_data = "welcome:create_account_confirm") # Принять и продолжить (создать аккаунт)
    builder.button(text = await db.GetLocaleText(7), callback_data = "welcome:create_account_rules") # Подробные правила
    builder.button(text = await db.GetLocaleText(6), callback_data = "welcome:main") # Назад в главное меню
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        text,
        reply_markup = builder.as_markup(),
        parse_mode = "HTML"
    )
    
# Создать аккаунт - полные правила    
@welcome_router.callback_query(F.data=="welcome:create_account_rules")
async def create_account_rules(callback: CallbackQuery):
    await callback.answer()
    
    text = await db.GetLocaleText(5003)
    
    builder = InlineKeyboardBuilder()
    
    builder.button(text = await db.GetLocaleText(8), callback_data = "welcome:create_account_rules_short") # Продолжить (к коротким правилам)
    builder.button(text = await db.GetLocaleText(6), callback_data = "welcome:main") # Назад в главное меню
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        text,
        reply_markup = builder.as_markup(),
        parse_mode = "HTML"
    )
    
# Создать аккаунт
@welcome_router.callback_query(F.data=="welcome:create_account_confirm")
async def create_account_confirm(callback: CallbackQuery):
    await callback.answer()
    
    telegram_id = callback.from_user.id
    player_id = await game.register_account(telegram_id)
    
    if player_id > 0:
        text = f"Аккаунт для пользователя {telegram_id} создан. Игровой id: {player_id}"
        await callback.message.edit_text(text)