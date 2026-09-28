from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from aiogram.dispatcher.event.bases import SkipHandler


from instances.game import game
from instances.db import db

dialog_router = Router()

#   Переменные-буферы для хранения краткосрочных данных между отправкой и получением данных, пока сервер активен (в рамках одной условной сессии)
current_users_dialog = {}
current_users_params = {}
current_users_input = {}
current_users_last_bot_message = {}
# Также можно добавить еще одну переменную с датой последнего обращения. Чтобы у данных от пользователей было время жизни и они через сколько то самоочищались

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
    
    current_dialog_id = None
    
    if player.show_dialog_mode == 2 and player.current_extra_dialog_id is not None:
        current_dialog_id = player.current_extra_dialog_id
    elif player.show_dialog_mode == 1 and player.current_dialog_id is not None:
        current_dialog_id = player.current_dialog_id
    else:
        await message.answer(
            "Error: no active dialog for player"
        )
        return
    print("dialog.py current_dialog_id: ", current_dialog_id)
    
    dialog = await game.dialogs.get_by_id(
        current_dialog_id
    )

    if dialog is None:
        await message.answer(
            "Error: dialog not found"
        )
        return
    else:
        #   Работа с сессионными переменными, а также передача их в событие открытия диалога и сохранение модифицированных значений, если там был обработчик
        params = current_users_params.get(message.chat.id, {})
        dialog, params = await game.dialogs.on_open_dialog_processor(dialog, params)
        
        current_users_dialog[message.chat.id] = dialog
        current_users_params[message.chat.id] = params
        
        dialog = await game.dialogs.render_view(
            dialog
        )

    builder = InlineKeyboardBuilder()

    for option in dialog.options:
        builder.button(
            text=option.text.text,
            callback_data=f"dialog:option:{option.id}"
        )

    builder.adjust(1)
    
    reply_markup=builder.as_markup()

    if edit:
        last_bot_message = current_users_last_bot_message.get(message.chat.id, None)
        # Если в сообщении изменился текст или reply_markup, то меняем его
        if last_bot_message is not None and (message.text != dialog.text.text or message.reply_markup != reply_markup):
            current_users_last_bot_message[message.chat.id] = await message.edit_text(
                dialog.text.text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            print("Сообщение не изменено в ответе, так как текст и reply_markup совпадают с предыдущим (последним) сообщением от бота для данного пользователя")
    else:
        current_users_last_bot_message[message.chat.id] = await message.answer(
            dialog.text.text,
            reply_markup=reply_markup,
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
        
    dialog = current_users_dialog.get(callback.message.chat.id, None)
    
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
    
    #   Работа с сессионными переменными, а также передача их в событие открытия диалога и сохранение модифицированных значений, если там был обработчик
    params = current_users_params.get(callback.message.chat.id, {})
    
    # Процессор нажатия кнопки для перехвата события закрытия диалога, после нажатия, но до обработки результатов нажатия
    dialog, option_selected, params = await game.dialogs.on_close_dialog_processor(dialog, option_selected, params)
    
    # Помечаем выбор, устанавливаем следующий дилаог и т.д., если это требуется в соответствии с кнопкой
    next_dialog_id = await game.players.choose_dialog_option(
        player=player,
        dialog=dialog,
        option=option_selected
    )

    if next_dialog_id is None:
        return

    # Обновляем сообщение, так как уже должен быть установлен следующий диалог
    await main(
        callback.message,
        edit=True,
        player=player
    )


# Обработчик для сообщений ввода текста в диалог 
@dialog_router.message(F.text)
async def echo_handler(message: Message):
    dialog = current_users_dialog.get(message.chat.id, None)
    if dialog is not None and dialog.input_type == 1:
        print("Пользователь ввел в диалог с разрешенным вводом текста: ", message.text)
        
        dialog = current_users_dialog.get(message.chat.id, None)
        params = current_users_params.get(message.chat.id, {})
        user_input = message.text
        
        valid, dialog, params, user_input, error_message = await game.dialogs.on_input_dialog_processor(dialog, params, user_input)
       
        current_users_dialog[message.chat.id] = dialog
        current_users_params[message.chat.id] = params       
        current_users_input[message.chat.id] = message.text
        
        # Если пользовательские ввод корректный (в процессоре проверили ожидаемый тип и прочее, и всё подошло
        # то показываем следующий диалог, указанный в диалоге ввода, иначе возвращаем к предыдущему
        if valid:
            if dialog.next_dialog_id is not None:
                player = await game.players.get_by_telegram_id(message.chat.id)
                if player is not None:
                    await game.players.choice_next_dialog(player, dialog)
                    
                dialog = await game.dialogs.get_by_id(
                    dialog.next_dialog_id
                )
                
                if dialog is None:
                    print("Следующий диалог по факту в базе не найден")
                    return
            else:
                print("После пользовательского ввода следующий диалог не установлен, так как он не указан в текущем диалоге")
        
        # Удаляем пользовательское сообщение с вводом и обновляем последнее сообщение бота
        #await message.delete()
        
        last_bot_message = current_users_last_bot_message.get(message.chat.id, None)
        print("last_bot_message", last_bot_message.text)
        
        if last_bot_message is not None:
            await main(
                last_bot_message,
                #edit=True
                edit=False
            )
        else:
            print("Последнее сообщение бота не нашлось")
            
    else:
        raise SkipHandler
    #await message.answer(f"Я получил твое сообщение. Ты написал: {message.text}")