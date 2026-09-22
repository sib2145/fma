from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import configparser

from instances import game

from menus.welcome import welcome_menu

config = configparser.ConfigParser()
config.read("config.ini")

allowed_users = config["access"].get("allowed_users", "")
ALLOWED_USERS = {
    int(user_id.strip())
    for user_id in allowed_users.split(",")
    if user_id.strip()
}

router = Router()

# Обработчик на команду /start
@router.message(CommandStart())
async def start(message: Message):
    menu = welcome_menu()

    await message.answer(
        menu.text,
        reply_markup=menu.keyboard
    )

async def start2(message: Message):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer(f"You don't have access to this bot. Your telegram id is: {message.from_user.id}")
        return
        
    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="Тестовое действие",
        callback_data="test",
    )

    await message.answer(
        "Привет тебе в игре FMA! Создай свой фентезийный магазин и управляй им!\n\nНачни с алхимической лавки. Смешивай зелья, нанимай и вербуй сильный персонал, продавай бродячим искаталем приключений или другим игрокам, повышай престиж лавки и её узнаваемость.\n\nЧто тут интересного:\n\n\- Искатели приключений независимы и могут иногда захаживать в твою лавку продать травы и купить зелья;\n\n-Ты можешь нанять искателей приключений на поиски и сбор трав и реагентов;\n\nРазные локальные и глобальные мировые события влияют на доступность и ценность трав, на востребованность и цену зелий;\n\nИскатели приключений попадаются разной редкости, рас и типов;Работники магазина со временем повышают уровень и меняют типа на более сильный. Более сильный - более эффективный.n\n- Давай задания работникам и авантюристам, а потом насладжася результатом;Лавка растет, развивается, приносит прибыль, открывает новые рецепты и возможности;- Новые рецепты для зелий можно открывать, а можно своровать у соседей, найти в странствиях авантюристов или неожиданно получить от клиента за деньги;- Игра не сильно отвлекает и напрягает, но позволяет скратить твоё время при скуке;- Никаких приложений, установок, тормозов - игра только через бот в этом диалоге.",
        reply_markup=keyboard.as_markup(),
    )
    
@router.callback_query(F.data=="welcome:button1")
async def button1_click(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("button 1 pressed")

# Обработчик для остальных сообщений    
@router.message(F.text)
async def echo_handler(message: Message):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer(f"You don't have access to this bot. Your telegram id is: {message.from_user.id}")
        return
        
    await message.answer(f"Я получил твое сообщение: {message.text}")


@router.callback_query()
async def handle_callback(callback: CallbackQuery):
    #if callback.message.from_user.id not in ALLOWED_USERS:
    #    await callback.message.answer(f"You don't have access to this bot. Your telegram id is: {callback.message.from_user.id}")
    #    return
    
    result = game.handle_action(
        player_id=callback.from_user.id,
        action=callback.data,
    )

    await callback.answer()

    await callback.message.edit_text(
        result,
    )