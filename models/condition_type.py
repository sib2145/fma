from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

class ConditionType(Base):
    __tablename__ = "condition_types"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    text_id: Mapped[int] = mapped_column(
        nullable=False
    )

    weight: Mapped[int] = mapped_column(
        nullable=False,
        default=1
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    
    allowed_operators = relationship(
        "ConditionTypeOperator",
        back_populates="condition_type",
    )