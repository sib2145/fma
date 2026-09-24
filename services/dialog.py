from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.dialog import Dialog
from models.dialog_option import DialogOption


from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from models.dialog import Dialog


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
                        .selectinload(DialogOption.text)
                )
                .where(Dialog.id == dialog_id)
            )

            dialog = result.scalar_one_or_none()

            if dialog is not None:
                dialog.options.sort(
                    key=lambda option: option.weight or 0
                )

            return dialog


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

            result = await session.execute(
                select(DialogOption.weight)
                .where(DialogOption.dialog_id == dialog_id)
                .order_by(DialogOption.weight.desc())
                .limit(1)
            )

            max_weight = result.scalar_one_or_none()

            weight = (max_weight or 0) + 1

            text_model = await self.text_service.create(
                session=session,
                text=text,
                locale_id=locale_id
            )

            option = DialogOption(
                dialog_id=dialog_id,
                text_id=text_model.id,
                weight=weight
            )

            session.add(option)
            await session.flush()

            await session.commit()

            return option.id


    async def get_option_by_id(
        self,
        option_id: int
    ) -> DialogOption | None:
        async with self.db.session_factory() as session:
            result = await session.execute(
                select(DialogOption)
                .options(
                    selectinload(DialogOption.text),
                    selectinload(DialogOption.dialog)
                    .selectinload(Dialog.options)
                    .selectinload(DialogOption.text),
                    selectinload(DialogOption.next_dialog)
                    .selectinload(Dialog.text)
                )
                .where(DialogOption.id == option_id)
            )

            option = result.scalar_one_or_none()

            if option is not None:
                option.dialog.options.sort(
                    key=lambda item: item.weight or 0
                )

            return option



    async def delete_option(
        self,
        option_id: int
    ) -> int | None:
        async with self.db.session_factory() as session:
            option = await session.get(
                DialogOption,
                option_id
            )

            if option is None:
                return None

            dialog_id = option.dialog_id

            await session.delete(option)
            await session.commit()

            return dialog_id

    async def move_option(
        self,
        option_id: int,
        direction: int
    ) -> int | None:
        async with self.db.session_factory() as session:
            option = await session.get(
                DialogOption,
                option_id
            )

            if option is None:
                return None

            result = await session.execute(
                select(DialogOption)
                .where(
                    DialogOption.dialog_id == option.dialog_id
                )
                .order_by(DialogOption.weight)
            )

            options = list(result.scalars())

            try:
                current_index = next(
                    i
                    for i, item in enumerate(options)
                    if item.id == option_id
                )
            except StopIteration:
                return None

            new_index = current_index + direction

            # Уже в начале/конце
            if new_index < 0 or new_index >= len(options):
                return option.dialog_id

            other_option = options[new_index]

            option.weight, other_option.weight = (
                other_option.weight,
                option.weight
            )

            await session.commit()

            return option.dialog_id

    async def normalize_option_weights(self):
        async with self.db.session_factory() as session:
            result = await session.execute(
                select(DialogOption)
                .order_by(
                    DialogOption.dialog_id,
                    DialogOption.id
                )
            )

            options = list(result.scalars())

            current_dialog_id = None
            weight = 0

            for option in options:
                if option.dialog_id != current_dialog_id:
                    current_dialog_id = option.dialog_id
                    weight = 1
                else:
                    weight += 1

                option.weight = weight

            await session.commit()


    async def set_next_dialog(
        self,
        option_id: int,
        next_dialog_id: int
    ) -> bool:
        async with self.db.session_factory() as session:
            option = await session.get(
                DialogOption,
                option_id
            )

            if option is None:
                return False

            dialog = await session.get(
                Dialog,
                next_dialog_id
            )

            if dialog is None:
                return False

            option.next_dialog_id = next_dialog_id

            await session.commit()

            return True

    async def unlink_dialog(
        self,
        option_id: int
    ) -> bool:
        async with self.db.session_factory() as session:
            option = await session.get(
                DialogOption,
                option_id
            )

            if option is None:
                return False

            option.next_dialog_id = None

            await session.commit()

            return True

    async def count(self) -> int:
        async with self.db.session_factory() as session:
            result = await session.execute(
                select(func.count(Dialog.id))
            )

            return result.scalar_one()

    async def get_page(
        self,
        page: int,
        per_page: int
    ) -> list[Dialog]:
        async with self.db.session_factory() as session:
            offset = (page - 1) * per_page

            result = await session.execute(
                select(Dialog)
                .options(
                    selectinload(Dialog.text)
                )
                .order_by(Dialog.id)
                .offset(offset)
                .limit(per_page)
            )

            return list(result.scalars())
