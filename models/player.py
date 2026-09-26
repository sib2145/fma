from datetime import datetime, UTC

from sqlalchemy import ForeignKey, Integer

from typing import Optional

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False
    )

    locale_id: Mapped[int] = mapped_column(
        nullable=False,
        default=1
    )

    join_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC)
    )

    last_active: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )

    current_dialog_id: Mapped[int | None] = mapped_column(
        ForeignKey("dialogs.id"),
        nullable=True
    )
    
    current_extra_dialog_id: Mapped[int | None] = mapped_column(
        ForeignKey("dialogs.id"),
        nullable=True
    )
    
    show_dialog_mode: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    
    current_dialog: Mapped[Optional["Dialog"]] = relationship(
        "Dialog",
        foreign_keys=[current_dialog_id]
    )
    
    current_extra_dialog: Mapped[Optional["Dialog"]] = relationship(
        "Dialog",
        foreign_keys=[current_extra_dialog_id]
    )