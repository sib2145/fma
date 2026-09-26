from typing import Optional

from sqlalchemy import ForeignKey, Integer, Text as SQLText, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.text import Text


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
        SQLText,
        nullable=True
    )

    weight: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    text_id: Mapped[int] = mapped_column(
        ForeignKey("texts.id"),
        nullable=False
    )

    next_dialog_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dialogs.id"),
        nullable=True
    )
    
    save_choice: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    dialog: Mapped["Dialog"] = relationship(
        "Dialog",
        back_populates="options",
        foreign_keys=[dialog_id]
    )

    text: Mapped["Text"] = relationship(
        "Text",
        foreign_keys=[text_id]
    )

    next_dialog: Mapped[Optional["Dialog"]] = relationship(
        "Dialog",
        foreign_keys=[next_dialog_id]
    )
