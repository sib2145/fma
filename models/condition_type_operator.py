from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class ConditionTypeOperator(Base):
    __tablename__ = "condition_type_operators"

    condition_type_id: Mapped[int] = mapped_column(
        ForeignKey("condition_types.id"),
        primary_key=True,
    )

    operator_type_id: Mapped[int] = mapped_column(
        ForeignKey("condition_operators.id"),
        primary_key=True,
    )

    condition_type = relationship(
        "ConditionType",
        back_populates="allowed_operators",
    )

    operator_type = relationship(
        "ConditionOperator",
    )
