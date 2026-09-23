from typing import Optional

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Dialog(Base):
    __tablename__ = "dialogs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    text_id: Mapped[int] = mapped_column(
        nullable=False
    )

    image: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    options: Mapped[list["DialogOption"]] = relationship(
        "DialogOption",
        back_populates="dialog",
        foreign_keys="DialogOption.dialog_id"
    )
