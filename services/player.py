from datetime import UTC, datetime

from sqlalchemy import delete, select

from models.player import Player
from models.dialog import Dialog
from models.dialog_option import DialogOption
from models.player_dialog_choice import PlayerDialogChoice

from views.player import PlayerView
from views.dialog import DialogView, DialogOptionView


class PlayerService:

    def __init__(self, db):
        self.db = db

    def _to_view(
        self,
        player: Player
    ) -> PlayerView:
        return PlayerView(
            id=player.id,
            telegram_id=player.telegram_id,
            locale_id=player.locale_id,
            join_date=player.join_date,
            last_active=player.last_active,
            current_dialog_id=player.current_dialog_id,
            current_extra_dialog_id=player.current_extra_dialog_id,
            show_dialog_mode=player.show_dialog_mode,
        )

    async def register(
        self,
        telegram_id: int,
        locale_id: int = 1
    ) -> PlayerView:

        async with self.db.session_factory() as session:
            result = await session.execute(
                select(Player).where(
                    Player.telegram_id == telegram_id
                )
            )

            player = result.scalar_one_or_none()

            if player is not None:
                return self._to_view(player)

            player = Player(
                telegram_id=telegram_id,
                locale_id=locale_id
            )

            session.add(player)

            await session.commit()
            await session.refresh(player)

            return self._to_view(player)

    async def update_last_active(
        self,
        player_id: int
    ) -> bool:

        async with self.db.session_factory() as session:
            player = await session.get(
                Player,
                player_id
            )

            if player is None:
                return False

            player.last_active = datetime.now(UTC)

            await session.commit()

            return True

    async def get_by_id(
        self,
        player_id: int
    ) -> PlayerView | None:

        async with self.db.session_factory() as session:
            player = await session.get(
                Player,
                player_id
            )

            if player is None:
                return None

            return self._to_view(player)

    async def get_by_telegram_id(
        self,
        telegram_id: int
    ) -> PlayerView | None:

        async with self.db.session_factory() as session:
            result = await session.execute(
                select(Player).where(
                    Player.telegram_id == telegram_id
                )
            )

            player = result.scalar_one_or_none()

            if player is None:
                return None

            return self._to_view(player)

    async def delete(
        self,
        player_id: int
    ) -> bool:

        async with self.db.session_factory() as session:
            player = await session.get(
                Player,
                player_id
            )

            if player is None:
                return False

            await session.delete(player)
            await session.commit()

            return True

    async def set_current_dialog(
        self,
        player_id: int,
        dialog_id: int | None,
        as_extra: bool = False
    ) -> bool:

        async with self.db.session_factory() as session:
            player = await session.get(
                Player,
                player_id
            )

            if player is None:
                return False

            if as_extra:
                player.current_extra_dialog_id = dialog_id
            else:
                player.current_dialog_id = dialog_id

            await session.commit()

            return True

    async def set_show_dialog_mode(
        self,
        player_id: int,
        mode: int,
    ) -> bool:

        async with self.db.session_factory() as session:
            player = await session.get(
                Player,
                player_id
            )

            if player is None:
                return False

            player.show_dialog_mode = mode

            await session.commit()

            return True


    async def choose_dialog_option(
        self,
        player: PlayerView,
        dialog: DialogView,
        option: DialogOptionView,
    ) -> int | None:
        async with self.db.session_factory() as session:
            db_player = await session.get(
                Player,
                player.id,
            )

            if db_player is None:
                print("Пользователь не найден")
                return None

            if option is None:
                print("Нажатая кнопка не передана")
                return None

            # Запоминаем режим, в котором игрок находился
            # до обработки выбранной кнопки.
            current_show_dialog_mode = player.show_dialog_mode

            # Определяем текущий диалог игрока в зависимости
            # от активного режима.
            if current_show_dialog_mode == 1:
                current_dialog_id = db_player.current_dialog_id

            elif current_show_dialog_mode == 2:
                current_dialog_id = db_player.current_extra_dialog_id

            else:
                print(
                    f"Неизвестный show_dialog_mode: "
                    f"{current_show_dialog_mode}"
                )
                return None

            if current_dialog_id is None:
                print("У пользователя нет активного диалога")
                return None

            # Защита от подделанного callback.
            # Кнопка должна принадлежать текущему диалогу игрока.
            if option.dialog_id != current_dialog_id:
                print("Кнопка должна принадлежать текущему диалогу игрока")
                return None

            # Сохраняем выбор только если это разрешено
            # настройками текущего диалога.
            if (
                dialog.save_choice
                and option.save_choice
                and current_show_dialog_mode == 1
            ):

                # ---------------------------------------------
                # Обычный режим:
                # только один выбор в рамках диалога.
                # ---------------------------------------------
                if not dialog.multiselect:
                    await session.execute(
                        delete(PlayerDialogChoice).where(
                            PlayerDialogChoice.player_id == db_player.id,
                            PlayerDialogChoice.dialog_id == current_dialog_id,
                        )
                    )

                    session.add(
                        PlayerDialogChoice(
                            player_id=db_player.id,
                            dialog_id=current_dialog_id,
                            option_id=option.id,
                        )
                    )

                # ---------------------------------------------
                # Multiselect:
                # несколько разных options в одном диалоге.
                # ---------------------------------------------
                else:
                    result = await session.execute(
                        select(PlayerDialogChoice.id)
                        .where(
                            PlayerDialogChoice.player_id == db_player.id,
                            PlayerDialogChoice.dialog_id == current_dialog_id,
                            PlayerDialogChoice.option_id == option.id,
                        )
                        .limit(1)
                    )

                    choice_exists = (
                        result.scalar_one_or_none() is not None
                    )

                    # Не добавляем один и тот же option повторно.
                    if not choice_exists:
                        session.add(
                            PlayerDialogChoice(
                                player_id=db_player.id,
                                dialog_id=current_dialog_id,
                                option_id=option.id,
                            )
                        )

            # ---------------------------------------------
            # Определяем следующий диалог.
            #
            # Приоритет:
            #
            # option.next_dialog_id
            #       ↓
            # dialog.next_dialog_id
            #       ↓
            # остаёмся без изменения
            # ---------------------------------------------

            next_dialog_id = None

            if option.next_dialog_id is not None:
                next_dialog_id = option.next_dialog_id

            elif dialog.next_dialog_id is not None:
                next_dialog_id = dialog.next_dialog_id

            if next_dialog_id is not None:

                # ---------------------------------------------
                # Определяем режим следующего диалога.
                #
                # Если option.show_dialog_mode не задан,
                # сохраняем текущий режим игрока.
                #
                # Если задан:
                # 1 → обычный режим
                # 2 → extra-режим
                # ---------------------------------------------
                next_show_dialog_mode = (
                    option.show_dialog_mode
                    if option.show_dialog_mode is not None
                    else current_show_dialog_mode
                )

                if not await self.set_dialog_state(
                    db_player,
                    next_dialog_id,
                    next_show_dialog_mode,
                ):
                    print(
                        f"Неизвестный show_dialog_mode: "
                        f"{next_show_dialog_mode}"
                    )
                    return None

                # ---------------------------------------------
                # Синхронизируем PlayerView.
                # ORM Player уже изменён через set_dialog_state().
                # ---------------------------------------------
                player.show_dialog_mode = next_show_dialog_mode

                if next_show_dialog_mode == 1:
                    player.current_dialog_id = next_dialog_id

                elif next_show_dialog_mode == 2:
                    player.current_extra_dialog_id = next_dialog_id

            # Сохраняем выбор и новое состояние игрока
            # одной транзакцией.
            await session.commit()

            return next_dialog_id




    async def choice_next_dialog(
        self,
        player: Player,
        dialog: Dialog,
    ) -> Player | None:
        """
        Переводит игрока на следующий диалог.

        Переданный dialog используется непосредственно и повторно
        из базы не загружается. Это важно, потому что dialog может
        быть изменён процессором перед вызовом этой функции.

        Перед переходом проверяем, что next_dialog_id действительно
        существует в базе.

        show_dialog_mode:
            1 -> current_dialog_id
            2 -> current_extra_dialog_id
        """

        if dialog.next_dialog_id is None:
            return player

        async with self.db.session_factory() as session:

            # Проверяем, существует ли следующий диалог.
            result = await session.execute(
                select(Dialog.id)
                .where(
                    Dialog.id == dialog.next_dialog_id
                )
                .limit(1)
            )

            next_dialog_id = result.scalar_one_or_none()

            if next_dialog_id is None:
                return None

            # Загружаем актуального игрока из текущей сессии,
            # чтобы изменение гарантированно попало в БД.
            db_player = await session.get(
                Player,
                player.id,
            )

            if db_player is None:
                return None

            if db_player.show_dialog_mode == 1:
                db_player.current_dialog_id = next_dialog_id

            elif db_player.show_dialog_mode == 2:
                db_player.current_extra_dialog_id = next_dialog_id

            else:
                return None

            await session.commit()

            # Синхронизируем переданный объект player.
            if db_player.show_dialog_mode == 1:
                player.current_dialog_id = next_dialog_id

            elif db_player.show_dialog_mode == 2:
                player.current_extra_dialog_id = next_dialog_id

            return player
            
    async def set_dialog_state(
        self,
        db_player: Player,
        dialog_id: int,
        show_dialog_mode: int,
    ) -> bool:
        if show_dialog_mode == 1:
            db_player.current_dialog_id = dialog_id

        elif show_dialog_mode == 2:
            db_player.current_extra_dialog_id = dialog_id

        else:
            return False

        db_player.show_dialog_mode = show_dialog_mode

        return True
