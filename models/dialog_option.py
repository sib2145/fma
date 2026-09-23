from typing import Optional

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class DialogOption(Base):
    __tablename__ = "dialog_options"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    dialog_id: Mapped[int] = mapped_column(
        ForeignKey("dialogs.id"),
        nullable=False
    )

    condition: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    weight: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    text_id: Mapped[int] = mapped_column(
        nullable=False
    )

    next_dialog_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dialogs.id"),
        nullable=True
    )

    dialog: Mapped["Dialog"] = relationship(
        "Dialog",
        back_populates="options",
        foreign_keys=[dialog_id]
    )

    next_dialog: Mapped[Optional["Dialog"]] = relationship(
        "Dialog",
        foreign_keys=[next_dialog_id]
    )
