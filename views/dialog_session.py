from dataclasses import dataclass, field
from typing import Any

from views.dialog import DialogView
from views.player import PlayerView


@dataclass
class DialogSession:
    """
    Сессионное состояние пользователя при работе
    с системой диалогов.
    """
    player: PlayerView | None = None

    dialog: DialogView | None = None

    processor_data: dict[str, Any] = field(
        default_factory=dict
    )

    user_input: str | None = None

    last_bot_message: Any | None = None