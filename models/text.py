from sqlalchemy import Text as SqlText
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Text(Base):
    __tablename__ = "texts"

    id: Mapped[int] = mapped_column(primary_key=True)
    locale_id: Mapped[int] = mapped_column(
        primary_key=True,
        default=1
    )
    text: Mapped[str | None] = mapped_column(SqlText)
