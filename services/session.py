from services.player import PlayerService

from views.dialog_session import DialogSession


class SessionService:
    telegram_sessions: dict[int, DialogSession] = {}

    def __init__(
        self,
        db,
        player_service: PlayerService,
    ):
        self.db = db
        self.player_service = player_service


    async def get_by_telegram_id(
        self,
        telegram_id: int,
    ) -> DialogSession:
        """
        Получает существующую сессию пользователя
        или создаёт новую.

        Если для Telegram-пользователя существует Player,
        он будет доступен через session.player.
        """

        if telegram_id not in self.telegram_sessions:
            self.telegram_sessions[telegram_id] = DialogSession()

        session = self.telegram_sessions[telegram_id]

        session.player = (
            await self.player_service.get_by_telegram_id(
                telegram_id
            )
        )

        return session
