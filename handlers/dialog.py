from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.dispatcher.event.bases import SkipHandler

from instances.game import game

from views.dialog_session import DialogSession

dialog_router = Router()

from config import START_EXTRA_DIALOG_ID

async def main(
    message: Message,
    edit: bool = False,
):
    """
    Отображает текущий диалог пользователя.
    """

    # --------------------------------------------------
    # Получаем session.
    # --------------------------------------------------
    session = await game.sessions.get_by_telegram_id(
        message.chat.id
    )

    player = session.player

    # Если диалог уже находится в session,
    # продолжаем с него.
    #
    # Это позволяет пользователю без Player
    # переходить между диалогами.
    if session.dialog is not None:
        current_dialog_id = session.dialog.id

    # Если Player отсутствует, начинаем
    # со стартового extra-диалога.
    elif player is None:
        current_dialog_id = START_EXTRA_DIALOG_ID

    else:
        current_dialog_id = None

        if (
            player.show_dialog_mode == 2
            and player.current_extra_dialog_id is not None
        ):
            current_dialog_id = (
                player.current_extra_dialog_id
            )

        elif (
            player.show_dialog_mode == 1
            and player.current_dialog_id is not None
        ):
            current_dialog_id = (
                player.current_dialog_id
            )

        else:
            await message.answer(
                "Error: no active dialog for player"
            )

            return

    print(
        "dialog.py current_dialog_id: ",
        current_dialog_id,
    )

    # --------------------------------------------------
    # Загружаем DialogView из БД.
    #
    # DialogView сам по себе не содержит
    # processor_data.
    #
    # Всё состояние пользователя находится
    # в session.
    # --------------------------------------------------

    dialog = await game.dialogs.get_by_id(
        current_dialog_id
    )

    if dialog is None:
        await message.answer(
            "Error: dialog not found"
        )

        return

    session.dialog = dialog

    # --------------------------------------------------
    # Processor открытия.
    # --------------------------------------------------

    session = (
        await game.dialogs.on_open_dialog_processor(
            session
        )
    )

    # --------------------------------------------------
    # Берём уже изменённый DialogView из session.
    # --------------------------------------------------

    dialog = session.dialog

    if dialog is None:
        await message.answer(
            "Error: dialog not found"
        )

        return

    # --------------------------------------------------
    # Рендерим текст и кнопки.
    # --------------------------------------------------

    dialog = await game.dialogs.render_view(
        dialog
    )

    session.dialog = dialog

    # --------------------------------------------------
    # Создаём Telegram keyboard.
    #
    # Индекс существует ТОЛЬКО здесь.
    #
    # Processor'ы его никогда не получают.
    # --------------------------------------------------

    builder = InlineKeyboardBuilder()

    for index, option in enumerate(
        dialog.options
    ):
        builder.button(
            text=option.text.text,
            callback_data=(
                f"dialog:option:{index}"
            ),
        )

    builder.adjust(1)

    reply_markup = builder.as_markup()

    # --------------------------------------------------
    # Редактирование существующего сообщения или отсылка нового.
    # --------------------------------------------------

    if edit:
        last_bot_message = (
            session.last_bot_message
        )

        if last_bot_message is not None:
            session.last_bot_message = (
                await last_bot_message.edit_text(
                    dialog.text.text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            )
        else:
            session.last_bot_message = (
                await message.answer(
                    dialog.text.text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            )

    else:
        session.last_bot_message = (
            await message.answer(
                dialog.text.text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        )



# --------------------------------------------------
# Нажатие кнопки диалога.
# --------------------------------------------------
@dialog_router.callback_query(
    F.data.regexp(
        r"^dialog:option:\d+$"
    )
)
async def dialog_option_callback(
    callback: CallbackQuery,
):
    await callback.answer()

    option_index = int(
        callback.data.split(":")[-1]
    )

    session = await game.sessions.get_by_telegram_id(
        callback.message.chat.id
    )

    player = session.player
    dialog = session.dialog

    # --------------------------------------------------
    # Если session потерялась, например после
    # перезапуска сервера, переоткрываем диалог.
    # --------------------------------------------------

    if dialog is None:
        print(
            "Диалог устарел"
        )

        await callback.message.delete()

        await main(
            callback.message
        )

        return

    # --------------------------------------------------
    # Индекс должен соответствовать существующей
    # кнопке текущего DialogView.
    #
    # ВАЖНО:
    # индекс используется только здесь.
    # --------------------------------------------------

    if (
        option_index < 0
        or option_index >= len(dialog.options)
    ):
        print(
            f"Недопустимый индекс кнопки: "
            f"{option_index}"
        )

        return

    # --------------------------------------------------
    # Получаем именно ту кнопку, которая была
    # отображена пользователю.
    # --------------------------------------------------

    option_selected = (
        dialog.options[option_index]
    )

    # --------------------------------------------------
    # Передаём событие в session.
    #
    # Теперь processors не знают ничего
    # об option_index.
    # --------------------------------------------------

    session.processor_data[
        "selected_option"
    ] = option_selected

    # --------------------------------------------------
    # Processor закрытия.
    # --------------------------------------------------

    session = (
        await game.dialogs.on_close_dialog_processor(
            session
        )
    )

    # --------------------------------------------------
    # После processor'а берём потенциально
    # изменённую кнопку.
    # Например, dialog 6 меняет
    # next_dialog_id / show_dialog_mode.
    # --------------------------------------------------

    option_selected = (
        session.processor_data.get(
            "selected_option"
        )
    )

    if option_selected is None:
        print(
            "selected_option отсутствует "
            "после on_close_dialog_processor"
        )

        return

    # --------------------------------------------------
    # Если игрок не зарегистрирован,
    # выбор не сохраняется в БД.
    #
    # Но переход между диалогами всё равно
    # происходит внутри session.
    # --------------------------------------------------

    if player is None:
        next_dialog_id = (
            option_selected.next_dialog_id
        )

        if next_dialog_id is None:
            next_dialog_id = (
                dialog.next_dialog_id
            )

        if next_dialog_id is None:
            return

        next_dialog = await game.dialogs.get_by_id(
            next_dialog_id
        )

        if next_dialog is None:
            return

        session.dialog = next_dialog

    # --------------------------------------------------
    # Стандартная обработка выбора
    # зарегистрированного игрока.
    # --------------------------------------------------

    else:
        next_dialog_id = (
            await game.players.choose_dialog_option(
                player=player,
                dialog=dialog,
                option=option_selected,
            )
        )

        if next_dialog_id is None:
            return

        # После сохранения в Player
        # main() восстановит актуальный диалог.
        session.dialog = None

    # --------------------------------------------------
    # Обновляем сообщение.
    #
    # main() загрузит новый DialogView,
    # но сохранит session.processor_data.
    #
    # Поэтому selected_option попадёт
    # в on_open нового цикла.
    # --------------------------------------------------

    await main(
        callback.message,
        edit=True,
    )



# --------------------------------------------------
# Обработчик текстового ввода.
# --------------------------------------------------
@dialog_router.message(F.text)
async def echo_handler(
    message: Message,
):
    session = await game.sessions.get_by_telegram_id(
        message.chat.id
    )

    dialog = session.dialog

    if (
        dialog is None
        or dialog.input_type != 1
    ):
        raise SkipHandler

    print(
        "Пользователь ввел в диалог "
        "с разрешенным вводом текста: ",
        message.text,
    )

    # --------------------------------------------------
    # Сохраняем пользовательский ввод в session.
    # --------------------------------------------------

    session.user_input = message.text

    # --------------------------------------------------
    # Processor пользовательского ввода.
    # --------------------------------------------------

    (
        valid,
        session,
        error_message,
    ) = await game.dialogs.on_input_dialog_processor(
        session
    )

    # --------------------------------------------------
    # Если processor вернул ошибку,
    # можно здесь использовать error_message.
    # Пока сохраняем старое поведение.
    # --------------------------------------------------

    if error_message is not None:
        print(
            "Ошибка пользовательского ввода:",
            error_message,
        )

    # --------------------------------------------------
    # Если ввод корректный, переходим
    # на следующий диалог.
    # --------------------------------------------------

    if valid:
        dialog = session.dialog

        if (
            dialog is not None
            and dialog.next_dialog_id is not None
        ):
            player = session.player

            if player is not None:
                await game.players.choice_next_dialog(
                    player,
                    dialog,
                )

                # Player теперь содержит новый
                # текущий диалог, поэтому заставляем
                # main() восстановить его из Player.
                session.dialog = None

            else:
                # Для незарегистрированного игрока
                # переход существует только в session.
                next_dialog = (
                    await game.dialogs.get_by_id(
                        dialog.next_dialog_id
                    )
                )

                if next_dialog is not None:
                    session.dialog = next_dialog

        else:
            print(
                "После пользовательского ввода "
                "следующий диалог не установлен, "
                "так как он не указан в текущем диалоге"
            )

    # --------------------------------------------------
    # После processor'а dialog мог измениться.
    # --------------------------------------------------

    dialog = session.dialog

    if dialog is None and session.player is None:
        return

    # --------------------------------------------------
    # main() определяет активный диалог:
    # для гостя — из session,
    # для игрока — из Player.
    # --------------------------------------------------

    await main(
        message,
        edit=False,
    )
