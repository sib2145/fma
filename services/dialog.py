from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.dialog import Dialog
from models.dialog_option import DialogOption


class DialogService:
    def __init__(self, db, text_service):
        self.db = db
        self.text_service = text_service

    async def get_by_id(self, dialog_id: int) -> Dialog | None:
        async with self.db.session_factory() as session:
            result = await session.execute(
                select(Dialog)
                .options(
                    selectinload(Dialog.text),
                    selectinload(Dialog.options)
                )
                .where(Dialog.id == dialog_id)
            )

            return result.scalar_one_or_none()


    async def create(
        self,
        text: str,
        locale_id: int = 1
    ) -> int:
        async with self.db.session_factory() as session:
            text_model = await self.text_service.create(
                session=session,
                text=text,
                locale_id=locale_id
            )

            dialog = Dialog(
                text_id=text_model.id
            )

            session.add(dialog)
            await session.flush()

            await session.commit()

            return dialog.id

    async def add_option(
        self,
        dialog_id: int,
        text: str,
        locale_id: int = 1
    ) -> int | None:
        async with self.db.session_factory() as session:
            dialog = await session.get(Dialog, dialog_id)

            if dialog is None:
                return None

            text_model = await self.text_service.create(
                session=session,
                text=text,
                locale_id=locale_id
            )

            option = DialogOption(
                dialog_id=dialog_id,
                text_id=text_model.id
            )

            session.add(option)
            await session.flush()

            await session.commit()

            return option.id
