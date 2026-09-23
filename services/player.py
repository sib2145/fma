from datetime import UTC, datetime

from sqlalchemy import select

from models.player import Player


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
        player_id: int,
        dialog_id: int | None
    ) -> bool:

        print("1. Открываем session")

        async with self.db.session_factory() as session:

            print("2. Получаем player")

            player = await session.get(Player, player_id)

            print("3. Player:", player)

            if player is None:
                return False

            player.current_dialog_id = dialog_id

            print("4. Установили current_dialog_id")

            await session.flush()
            print("5. Flush выполнен")

            await session.commit()
            print("6. Commit выполнен")

            return True