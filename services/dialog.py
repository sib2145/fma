from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.dialog import Dialog


class DialogService:
    def __init__(self, db):
        self.db = db

    async def get_by_id(self, dialog_id: int) -> Dialog | None:
        async with self.db.session_factory() as session:
            result = await session.execute(
                select(Dialog)
                .options(
                    selectinload(Dialog.options)
                )
                .where(Dialog.id == dialog_id)
            )

            return result.scalar_one_or_none()