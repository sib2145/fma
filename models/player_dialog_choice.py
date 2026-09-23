from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class PlayerDialogChoice(Base):
    __tablename__ = "player_dialog_choices"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"),
        nullable=False
    )

    dialog_id: Mapped[int] = mapped_column(
        ForeignKey("dialogs.id"),
        nullable=False
    )

    option_id: Mapped[int] = mapped_column(
        ForeignKey("dialog_options.id"),
        nullable=False
    )

    player = relationship("Player")
    dialog = relationship("Dialog")
    option = relationship("DialogOption")
