from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.dialog import Dialog
from models.dialog_option import DialogOption


from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from models.dialog import Dialog

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.text import Text

from models.condition import Condition
    

class DialogService:
    def __init__(self, db, text_service):
        self.db = db
        self.text_service = text_service
        
    async def on_open_dialog_processor(self, dialog):
        print("open dialog processor, id: ", dialog.id)
        if dialog.id == 1:
            pass
            #dialog.text.text = "123"
            dialog.options[0].text.text = "222"
        
        return dialog
        
    async def on_close_dialog_processor(self, dialog, option_selected):
        print("close dialog processor, id: ", dialog.id)
        return dialog, option_selected

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
                
            dialog = await self.on_open_dialog_processor(dialog)

            return dialog
            
    #async def get_by_id_processed(self, dialog_id: int):
    #    dialog = await self.get_by_id(dialog_id)
    #    if Dialog != None:
    #        options = {}
    #        for option in dialog.options:
    #            option[option.id] = 
    #        return dialog_id, dialog.text.text


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

    async def search(
        self,
        search_text: str,
        locale_id: int = 1
    ) -> list[Dialog]:
        async with self.db.session_factory() as session:
            result = await session.execute(
                select(Dialog)
                .join(Text, Dialog.text_id == Text.id)
                .options(
                    selectinload(Dialog.text)
                )
                .where(
                    Text.locale_id == locale_id,
                    Text.text.ilike(f"%{search_text}%")
                )
                .order_by(Dialog.id)
            )

            return list(result.scalars())
            
    async def get_option_for_dialog(
        self,
        option_id: int,
        dialog_id: int
    ) -> DialogOption | None:

        async with self.db.session_factory() as session:
            result = await session.execute(
                select(DialogOption)
                .where(
                    DialogOption.id == option_id,
                    DialogOption.dialog_id == dialog_id
                )
            )

            return result.scalar_one_or_none()

    async def add_condition(
        self,
        condition_type_id: int,
        operator_type_id: int,
        value1: str | None = None,
        value2: str | None = None,
        dialog_id: int | None = None,
        option_id: int | None = None
    ) -> int | None:
        if (dialog_id is None) == (option_id is None):
            return None

        async with self.db.session_factory() as session:
            condition = Condition(
                dialog_id=dialog_id,
                option_id=option_id,
                condition_type_id=condition_type_id,
                operator_type_id=operator_type_id,
                value1=value1,
                value2=value2
            )

            session.add(condition)

            await session.flush()
            await session.commit()

            return condition.id