from dataclasses import dataclass, field
from typing import Any

from views.text import TextView


@dataclass
class DialogOptionView:
    id: int | None
    dialog_id: int | None

    condition: str | None
    weight: int | None

    text: TextView

    next_dialog_id: int | None
    next_dialog_text: TextView | None
    
    show_dialog_mode: int | None

    save_choice: bool
    
    # Флаг для процессоров для лучшей идентификации динамических кнопок. Не связан с id из базы данных.
    processor_flag: str | None = None


@dataclass
class DialogView:
    id: int

    text_id: int
    text: TextView

    image: str | None

    next_dialog_id: int | None
    next_dialog_comment: str | None
    next_dialog_text: TextView | None

    save_choice: bool
    multiselect: bool

    is_extra: bool
    input_type: int

    comment: str | None

    options: list[DialogOptionView] = field(
        default_factory=list
    )

    # Дополнительные переменные,
    # которые могут добавлять processors.
    template_context: dict[str, Any] = field(
        default_factory=dict
    )
    