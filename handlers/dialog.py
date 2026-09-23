from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from instances.game import game
from instances.db import db

dialog_router = Router()

async def main(message: Message, edit = False):

    player = await game.players.get_by_telegram_id(message.chat.id)
    if player == None:
        return
        
    if player.current_dialog_id == None:
        await message.answer("Error: no active dialog for player")
        return
        
    dialog = await game.dialogs.get_by_id(player.current_dialog_id)
    
    text = await db.GetLocaleText(dialog.text_id)
    
    if text == None:
        await message.answer("Error: no locale text for this dialog")
        return
    
    builder = InlineKeyboardBuilder()
    
    options = sorted(dialog.options, key=lambda option: option.weight or 0)
    
    for option in dialog.options:
        builder.button(text = await db.GetLocaleText(option.text_id), callback_data = "dialog:button1")
        
        
    #builder.button(text = await db.GetLocaleText(2), callback_data = "welcome:create_account_rules_short") # Создать аккаунт - краткие правила
    #builder.button(text = await db.GetLocaleText(3), callback_data = "welcome:rating") # Рейтинг игроков
    #builder.button(text = await db.GetLocaleText(4), callback_data = "welcome:world_stat") # Статистика по миру
    
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