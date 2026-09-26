from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from instances.game import game
from instances.db import db

dialog_router = Router()

current_players_dialog = {}

async def main(
    message: Message,
    edit: bool = False,
    player=None
):
    if player is None:
        player = await game.players.get_by_telegram_id(
            message.chat.id
        )

    if player is None:
        return

    if player.current_dialog_id is None:
        await message.answer(
            "Error: no active dialog for player"
        )
        return

    dialog = await game.dialogs.get_by_id(
        player.current_dialog_id
    )
    
    current_players_dialog[message.chat.id] = dialog

    if dialog is None:
        await message.answer(
            "Error: dialog not found"
        )
        return

    builder = InlineKeyboardBuilder()

    for option in dialog.options:
        builder.button(
            text=option.text.text,
            callback_data=f"dialog:option:{option.id}"
        )

    builder.adjust(1)

    if edit:
        await message.edit_text(
            dialog.text.text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            dialog.text.text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

        
@dialog_router.callback_query(
    F.data.regexp(r"^dialog:option:\d+$")
)
async def dialog_option_callback(
    callback: CallbackQuery
):
    await callback.answer()

    option_id = int(
        callback.data.split(":")[-1]
    )
    
    option = await game.dialogs.get_option_by_id(option_id)
    
    if option is None:
        return

    player = await game.players.get_by_telegram_id(
        callback.from_user.id
    )

    if player is None:
        return
        
    dialog = current_players_dialog.get(callback.message.chat.id, None)
    
    if dialog is None:
        # Если диалог устарел, то есть между открытием и нажатием сервер был перезагружен, то переотправляем последнее сообщение
        print("Диалог устарел")
        await callback.message.delete()
        await main(callback.message)
        return
        
    option_selected = None
    for option in dialog.options:
        if option.id == option_id:
            option_selected = option
            break
    
    # Процессор нажатия кнопки для перехвата события закрытия диалога, после нажатия, но до обработки результатов нажатия
    dialog, option_selected = await game.dialogs.on_close_dialog_processor(dialog, option_selected)

    # Помечаем выбор, устанавливаем следующий дилаог и т.д., если это требуется в соответствии с кнопкой
    player = await game.players.choose_dialog_option(
        player=player,
        #option_id=option_id
        option=option_selected
    )

    if player is None:
        return

    # Обновляем сообщение, так как уже должен быть установлен следующий диалог
    await main(
        callback.message,
        edit=True,
        player=player
    )
