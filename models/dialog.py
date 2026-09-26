from sqlalchemy import ForeignKey, Text as SQLText
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean

from models.base import Base
from models.text import Text

from typing import Optional


class Dialog(Base):
    __tablename__ = "dialogs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    text_id: Mapped[int] = mapped_column(
        ForeignKey("texts.id"),
        nullable=False
    )

    image: Mapped[Optional[str]] = mapped_column(
        SQLText,
        nullable=True
    )
    
    next_dialog_id: Mapped[int | None] = mapped_column(
        ForeignKey("dialogs.id"),
        nullable=True,
    )

    save_choice: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    multiselect: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    is_extra: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    text: Mapped["Text"] = relationship(
        "Text",
        foreign_keys=[text_id]
    )

    next_dialog: Mapped["Dialog | None"] = relationship(
        "Dialog",
        remote_side=[id],
        foreign_keys=[next_dialog_id],
    )

    options: Mapped[list["DialogOption"]] = relationship(
        "DialogOption",
        back_populates="dialog",
        foreign_keys="DialogOption.dialog_id"
    )
    
