from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base

class ConditionOperator(Base):
    __tablename__ = "condition_operators"

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