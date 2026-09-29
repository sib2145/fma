from dataclasses import dataclass, field
from typing import Any

from views.dialog import DialogView


@dataclass
class DialogSession:
    """
    Сессионное состояние пользователя при работе
    с системой диалогов.
    """

    dialog: DialogView | None = None

    processor_data: dict[str, Any] = field(
        default_factory=dict
    )

    user_input: str | None = None

    last_bot_message: Any | None = None