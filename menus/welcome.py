from dataclasses import dataclass

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from instances import db


@dataclass
class Menu:
    text: str
    keyboard: InlineKeyboardMarkup


def welcome_menu() -> Menu:
    builder = InlineKeyboardBuilder()
    
    builder.button(text="Кнопка 1", callback_data="welcome:button1")
    builder.button(text="Кнопка 2", callback_data="welcome:button2")
    
    return Menu(
        text = db.GetLocaleText(1),
        keyboard=builder.as_markup()
    )
