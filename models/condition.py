from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

class Condition(Base):
    __tablename__ = "conditions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    dialog_id: Mapped[int | None] = mapped_column(
        ForeignKey("dialogs.id"),
        nullable=True
    )

    option_id: Mapped[int | None] = mapped_column(
        ForeignKey("dialog_options.id"),
        nullable=True
    )

    condition_type_id: Mapped[int] = mapped_column(
        ForeignKey("condition_types.id"),
        nullable=False
    )

    operator_type_id: Mapped[int] = mapped_column(
        ForeignKey("condition_operators.id"),
        nullable=False
    )

    value1: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    value2: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    dialog = relationship("Dialog")
    option = relationship("DialogOption")
    condition_type = relationship("ConditionType")
    operator_type = relationship("ConditionOperator")