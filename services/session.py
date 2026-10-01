from services.player import PlayerService

from views.dialog_session import DialogSession

class SessionService:

    telegram_sessions: dict[int, DialogSession] = {}


    def __init__(
        self,
        db,
        player_service: PlayerService
    ):
        self.db = db,
        self.player_service = player_service


    def get_by_telegram_id(
        self,
        chat_id: int,
    ) -> DialogSession:
        """
        Получает существующую сессию пользователя
        или создаёт новую.
        """

        if chat_id not in self.telegram_sessions:
            self.telegram_sessions[chat_id] = DialogSession()

        return self.telegram_sessions[chat_id]
