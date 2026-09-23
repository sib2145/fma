from sqlalchemy import ForeignKey, Text as SQLText
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    text: Mapped["Text"] = relationship(
        "Text",
        foreign_keys=[text_id]
    )

    options: Mapped[list["DialogOption"]] = relationship(
        "DialogOption",
        back_populates="dialog",
        foreign_keys="DialogOption.dialog_id"
    )
    
