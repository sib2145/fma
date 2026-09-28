from dataclasses import dataclass


@dataclass
class TextView:
    id: int
    locale_id: int

    # Исходный шаблон из БД.
    template: str

    # Текущий отрендеренный текст.
    text: str
