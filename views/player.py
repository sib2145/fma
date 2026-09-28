from dataclasses import dataclass
from datetime import datetime


@dataclass
class PlayerView:
    id: int
    telegram_id: int

    locale_id: int

    join_date: datetime
    last_active: datetime | None

    current_dialog_id: int | None
    current_extra_dialog_id: int | None

    show_dialog_mode: int
