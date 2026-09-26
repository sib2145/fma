from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import configparser

from instances.game import game

from handlers.dialog import main as dialog_show

config = configparser.ConfigParser()
config.read("config.ini")

allowed_users = config["access"].get("allowed_users", "")
ALLOWED_USERS = {
    int(user_id.strip())
    for user_id in allowed_users.split(",")
    if user_id.strip()
}

router = Router()

async def enter_adm(message: Message, edit = False):
    player = await game.players.get_by_telegram_id(message.chat.id)
    if player:
        # Если игрок зарегистрирован, переключаем в режим служебного диалога и ставим диалог админа
        await game.players.set_show_dialog_mode(player, 2)
        await game.players.set_current_dialog(player, 5, True)
        await dialog_show(message, edit)
        
@router.callback_query(F.data=="adm:main")
async def enter_adm_callback(callback: CallbackQuery):
    await callback.answer()
    await enter_adm(callback.message, True)
    
@router.message(F.text == "/adm")
async def enter_adm_command(message: Message):
    await enter_adm(message)
    
async def enter_game(message: Message, edit = False):
    player = await game.players.get_by_telegram_id(message.chat.id)
    if player and player.current_dialog_id is not None:
        # Если игрок зарегистрирован и у него есть текущий сюжетный диалог, переключаем в режим сюжетного диалога и обновляем
        await game.players.set_show_dialog_mode(player, 1)
        await dialog_show(message, edit)
        
@router.callback_query(F.data=="game:main")
async def enter_game_callback(callback: CallbackQuery):
    await callback.answer()
    await enter_game(callback.message, True)
    
@router.message(F.text == "/game")
async def enter_game_command(message: Message):
    await enter_game(message)





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