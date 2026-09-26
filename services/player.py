from datetime import UTC, datetime

from sqlalchemy import delete, select

from models.player import Player

from models.dialog import Dialog
from models.dialog_option import DialogOption
from models.player_dialog_choice import PlayerDialogChoice



class PlayerService:

    def __init__(self, db):
        self.db = db

    async def register(
        self,
        telegram_id: int,
        locale_id: int = 1
    ) -> Player:

        async with self.db.session_factory() as session:

            result = await session.execute(
                select(Player).where(
                    Player.telegram_id == telegram_id
                )
            )

            player = result.scalar_one_or_none()

            if player is not None:
                return player

            player = Player(
                telegram_id=telegram_id,
                locale_id=locale_id
            )

            session.add(player)
            await session.commit()
            await session.refresh(player)

            return player

    async def update_last_active(self, player_id: int) -> bool:
        async with self.db.session_factory() as session:

            player = await session.get(Player, player_id)

            if player is None:
                return False

            player.last_active = datetime.now(UTC)

            await session.commit()

            return True


    async def get_by_id(self, player_id: int) -> Player | None:
        async with self.db.session_factory() as session:
            return await session.get(Player, player_id)

    async def get_by_telegram_id(
        self,
        telegram_id: int
    ) -> Player | None:

        async with self.db.session_factory() as session:
            result = await session.execute(
                select(Player).where(
                    Player.telegram_id == telegram_id
                )
            )

            return result.scalar_one_or_none()

    async def delete(self, player_id: int) -> bool:
        async with self.db.session_factory() as session:

            player = await session.get(Player, player_id)

            if player is None:
                return False

            await session.delete(player)
            await session.commit()

            return True
            
    async def set_current_dialog(
        self,
        player: Player,
        dialog_id: int | None,
        as_extra: bool = False 
    ) -> bool:
        async with self.db.session_factory() as session:
            db_player = await session.get(
                Player,
                player.id
            )
            
            if db_player is None:
                return False
            if as_extra:
                db_player.current_extra_dialog_id = dialog_id
            else:
                db_player.current_dialog_id = dialog_id

            await session.commit()

            return True
            
    async def set_show_dialog_mode(
        self,
        player: Player,
        mode: int,
    ) -> bool:
        async with self.db.session_factory() as session:
            db_player = await session.get(
                Player,
                player.id
            )

            if db_player is None:
                return False
                
            db_player.show_dialog_mode = mode

            await session.commit()

            return True


    async def choose_dialog_option(
        self,
        player: Player,
        dialog: Dialog,
        option: DialogOption,
    ) -> int | None:
        async with self.db.session_factory() as session:
            db_player = await session.get(
                Player,
                player.id,
            )

            if db_player is None:
                print("Пользователь не найден")
                return None

            if (db_player.current_dialog_id is None) or (db_player.current_extra_dialog_id is None):
                print("У пользователя нет активных диалогов")
                return None

            if option is None:
                print("Нажатая кнопка не передана")
                return None

            # Защита от подделанного callback.
            # Кнопка должна принадлежать текущему диалогу игрока.
            if (option.dialog_id != db_player.current_dialog_id) and (option.dialog_id != db_player.current_extra_dialog_id):
                print("Кнопка должна принадлежать текущему диалогу игрока")
                return None

            # Сохраняем выбор только если это разрешено
            # настройками текущего диалога.
            if dialog.save_choice and option.save_choice and player.show_dialog_mode == 1:

                # ---------------------------------------------
                # Обычный режим:
                # только один выбор в рамках диалога.
                # ---------------------------------------------
                if not dialog.multiselect:
                    await session.execute(
                        delete(PlayerDialogChoice).where(
                            PlayerDialogChoice.player_id == db_player.id,
                            PlayerDialogChoice.dialog_id == db_player.current_dialog_id,
                        )
                    )

                    session.add(
                        PlayerDialogChoice(
                            player_id=db_player.id,
                            dialog_id=db_player.current_dialog_id,
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
                            PlayerDialogChoice.dialog_id == db_player.current_dialog_id,
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
                                dialog_id=db_player.current_dialog_id,
                                option_id=option.id,
                            )
                        )
            await session.commit()

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
                #print("next_dialog_id: ", next_dialog_id)
                if player.show_dialog_mode == 1:
                    await self.set_current_dialog(player, next_dialog_id, False)
                    player.current_dialog_id = next_dialog_id
                elif player.show_dialog_mode == 2:
                    await self.set_current_dialog(player, next_dialog_id, True)
                    player.current_extra_dialog_id = next_dialog_id
                else:
                    print(f"Неизвестный show_dialog_mode: {player.show_dialog_mode}")
                #db_player.current_dialog_id = next_dialog_id

            #await session.commit()

            return next_dialog_id
