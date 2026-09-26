from datetime import UTC, datetime

from sqlalchemy import select

from models.player import Player

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
        dialog_id: int
    ) -> bool:
        async with self.db.session_factory() as session:
            db_player = await session.get(
                Player,
                player.id
            )

            if db_player is None:
                return False

            db_player.current_dialog_id = dialog_id

            await session.commit()

            return True


    async def choose_dialog_option(
        self,
        player: Player,
        #option_id: int
        option: DialogOption
    ) -> Player | None:
        async with self.db.session_factory() as session:
            db_player = await session.get(
                Player,
                player.id
            )

            if db_player is None:
                return None

            if db_player.current_dialog_id is None:
                return None

            #option = await session.get(
            #   DialogOption,
            #    option_id
            #)

            if option is None:
                return None

            # Защита от подделанного callback.
            # Кнопка должна принадлежать текущему диалогу игрока.
            if option.dialog_id != db_player.current_dialog_id:
                return None

            # Пока кнопка никуда не ведёт.
            if option.next_dialog_id is None:
                return None

            choice = PlayerDialogChoice(
                player_id=db_player.id,
                dialog_id=db_player.current_dialog_id,
                option_id=option.id
            )

            session.add(choice)

            db_player.current_dialog_id = option.next_dialog_id

            await session.commit()

            # Обновляем объект, который был передан
            # в сервис, чтобы его можно было передать дальше
            # в main() без дополнительного запроса.
            player.current_dialog_id = db_player.current_dialog_id

            return player
