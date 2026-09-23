from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

import configparser

from instances.game import game
from instances.db import db

from models.dialog_option import DialogOption

config = configparser.ConfigParser()
config.read("config.ini")

admin_users = config["access"].get("admin_users", "")
ADMIN_USERS = {
    int(user_id.strip())
    for user_id in admin_users.split(",")
    if user_id.strip()
}


class AdminFilter(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        return event.from_user.id in ADMIN_USERS


admin_router = Router()

admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())

class AddDialogState(StatesGroup):
    waiting_for_text = State()
    
class ViewDialogState(StatesGroup):
    waiting_for_id = State()
    
class AddDialogOptionState(StatesGroup):
    waiting_for_text = State()
    
class EditDialogOptionState(StatesGroup):
    waiting_for_text = State()



async def main(message: Message, edit = False):
    text = await db.GetLocaleText(5004)
    
    builder = InlineKeyboardBuilder()
    
    builder.button(text = await db.GetLocaleText(11), callback_data = "admin:dialogs:main")

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

@admin_router.callback_query(F.data == "admin:main")
async def main_callback(callback: CallbackQuery):
    await callback.answer()
    await main(callback.message, True)
    
@admin_router.message(F.text == "/admin")
async def main_callback(message: Message):
    await main(message)
    
@admin_router.callback_query(F.data == "admin:dialogs:main")
async def show_dialogs_main(
    callback: CallbackQuery,
    #state: FSMContext
):
    await callback.answer()
    #await state.clear()

    text = await db.GetLocaleText(5005)

    builder = InlineKeyboardBuilder()

    builder.button(
        text=await db.GetLocaleText(12),
        callback_data="admin:dialogs:add"
    )
    builder.button(
        text=await db.GetLocaleText(13),
        callback_data="admin:dialogs:view"
    )
    builder.button(
        text=await db.GetLocaleText(14),
        callback_data="admin:dialogs:list"
    )
    builder.button(
        text=await db.GetLocaleText(15),
        callback_data="admin:dialogs:search"
    )

    builder.adjust(1)

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )




@admin_router.callback_query(F.data == "admin:dialogs:add")
async def add_dialog_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    builder = InlineKeyboardBuilder()

    builder.button(
        text="Отмена",
        callback_data="admin:dialogs:main"
    )

    builder.adjust(1)

    await state.set_state(AddDialogState.waiting_for_text)

    await callback.message.edit_text(
        "Введите текст диалога:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )



@admin_router.message(AddDialogState.waiting_for_text, F.text)
async def add_dialog_text(
    message: Message,
    state: FSMContext
):
    dialog_id = await game.dialogs.create(
        text=message.text
    )

    await state.clear()

    await message.answer(
        f"Диалог создан. ID: {dialog_id}"
    )
    
@admin_router.callback_query(F.data == "admin:dialogs:view")
async def view_dialog_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    builder = InlineKeyboardBuilder()

    builder.button(
        text="Отмена",
        callback_data="admin:dialogs:main"
    )

    builder.adjust(1)

    await state.set_state(ViewDialogState.waiting_for_id)

    await callback.message.edit_text(
        "Введите ID диалога:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@admin_router.message(ViewDialogState.waiting_for_id, F.text)
async def view_dialog_id(
    message: Message,
    state: FSMContext
):
    try:
        dialog_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "⚠️ ID диалога должен быть числом."
        )
        return

    dialog = await game.dialogs.get_by_id(dialog_id)

    if dialog is None:
        await message.answer(
            "⚠️ Диалог с таким ID не найден."
        )
        return

    await state.clear()

    await show_dialog(message, dialog)


@admin_router.callback_query(
    F.data.startswith("admin:dialogs:view:")
)
async def open_dialog_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    dialog_id = int(callback.data.split(":")[-1])

    dialog = await game.dialogs.get_by_id(dialog_id)

    if dialog is None:
        await callback.message.edit_text(
            "⚠️ Диалог не найден."
        )
        return

    await state.clear()

    await show_dialog(
        callback.message,
        dialog,
        edit=True
    )


async def show_dialog(
    message: Message,
    dialog,
    edit: bool = False
):
    text = dialog.text.text

    buttons_count = len(dialog.options)

    text += (
        f"\n\n"
        f"<b>Количество кнопок:</b> {buttons_count}"
    )

    builder = InlineKeyboardBuilder()

    builder.button(
        text="Редактировать текст",
        callback_data=f"admin:dialogs:edit:{dialog.id}"
    )

    builder.button(
        text="Добавить изображение",
        callback_data=f"admin:dialogs:image:{dialog.id}"
    )

    builder.button(
        text="Добавить кнопку",
        callback_data=f"admin:dialogs:option:add:{dialog.id}"
    )
    
    for option in dialog.options:
        builder.button(
            text=f"Кнопка: {option.text.text}",
            callback_data=f"admin:dialogs:option:view:{option.id}"
        )

    builder.button(
        text="Назад",
        callback_data="admin:dialogs:main"
    )

    builder.adjust(1)

    if edit:
        await message.edit_text(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )



@admin_router.callback_query(
    F.data.startswith("admin:dialogs:option:add:")
)
async def add_dialog_option_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    dialog_id = int(
        callback.data.split(":")[-1]
    )

    await state.update_data(
        dialog_id=dialog_id
    )

    await state.set_state(
        AddDialogOptionState.waiting_for_text
    )

    builder = InlineKeyboardBuilder()

    builder.button(
        text="Отмена",
        callback_data=f"admin:dialogs:view:{dialog_id}"
    )

    builder.adjust(1)

    await callback.message.edit_text(
        "Введите текст кнопки:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@admin_router.message(
    AddDialogOptionState.waiting_for_text,
    F.text
)
async def add_dialog_option_text(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    dialog_id = data["dialog_id"]
    option_text = message.text

    await game.dialogs.add_option(
        dialog_id=dialog_id,
        text=option_text
    )

    await state.clear()

    dialog = await game.dialogs.get_by_id(dialog_id)

    if dialog is not None:
        await show_dialog(message, dialog)

async def show_dialog_option(
    message: Message,
    option: DialogOption,
    edit: bool = False
):
    text = (
        f"<b>Кнопка:</b> {option.text.text}\n"
        f"<b>Следующий диалог:</b> "
    )

    if option.next_dialog_id is not None:
        text += str(option.next_dialog_id)

    builder = InlineKeyboardBuilder()

    builder.button(
        text="Редактировать текст",
        callback_data=f"admin:dialogs:option:edit:{option.id}"
    )

    builder.button(
        text="Удалить кнопку",
        callback_data=f"admin:dialogs:option:delete:{option.id}"
    )

    builder.button(
        text="Переместить вверх",
        callback_data=f"admin:dialogs:option:up:{option.id}"
    )

    builder.button(
        text="Переместить вниз",
        callback_data=f"admin:dialogs:option:down:{option.id}"
    )

    builder.button(
        text="Связанный диалог",
        callback_data=f"admin:dialogs:view:{option.next_dialog_id}"
    )

    builder.button(
        text="Отвязать диалог",
        callback_data=f"admin:dialogs:option:unlink:{option.id}"
    )

    builder.button(
        text="Назначить диалог",
        callback_data=f"admin:dialogs:option:link:{option.id}"
    )

    builder.button(
        text="Назад",
        callback_data=f"admin:dialogs:view:{option.dialog_id}"
    )

    builder.adjust(1)

    if edit:
        await message.edit_text(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )


@admin_router.callback_query(
    F.data.startswith("admin:dialogs:option:view:")
)
async def view_dialog_option_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    option_id = int(callback.data.split(":")[-1])

    option = await game.dialogs.get_option_by_id(option_id)

    if option is None:
        await callback.message.edit_text(
            "⚠️ Кнопка не найдена."
        )
        return

    await state.clear()

    await show_dialog_option(
        callback.message,
        option,
        edit=True
    )

@admin_router.callback_query(
    F.data.startswith("admin:dialogs:option:edit:")
)
async def edit_dialog_option_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()

    option_id = int(callback.data.split(":")[-1])

    await state.update_data(
        option_id=option_id
    )

    await state.set_state(
        EditDialogOptionState.waiting_for_text
    )

    builder = InlineKeyboardBuilder()

    builder.button(
        text="Отмена",
        callback_data=f"admin:dialogs:option:view:{option_id}"
    )

    builder.adjust(1)

    await callback.message.edit_text(
        "Введите новый текст кнопки:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@admin_router.message(
    EditDialogOptionState.waiting_for_text,
    F.text
)
async def edit_dialog_option_text(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    option_id = data["option_id"]

    option = await game.dialogs.get_option_by_id(option_id)

    if option is None:
        await state.clear()

        await message.answer(
            "⚠️ Кнопка не найдена."
        )
        return

    updated = await game.texts.update(
        text_id=option.text_id,
        text=message.text
    )

    if not updated:
        await state.clear()

        await message.answer(
            "⚠️ Текст кнопки не найден."
        )
        return

    await state.clear()

    option = await game.dialogs.get_option_by_id(option_id)

    await show_dialog_option(
        message,
        option
    )
