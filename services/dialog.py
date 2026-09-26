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


from dataclasses import dataclass, field
from enum import Enum

from models.condition import Condition
from models.condition_type import ConditionType
from models.player_dialog_choice import PlayerDialogChoice

from services.condition import (
    ConditionExpression,
    ConditionGroup,
    ConditionNode,
    ConditionParser,
    ConditionParseError,
    LogicalOperator,
)


    

class DialogService:
    def __init__(self, db, text_service):
        self.db = db
        self.text_service = text_service
        
    async def on_open_dialog_processor(self, dialog):
        print("open dialog processor, id: ", dialog.id)
        if dialog.id == 1:
            pass
            #dialog.text.text = "123"
            #dialog.options[0].text.text = "222"
        
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
            
            
    async def check_conditions(
        self,
        player_id: int,
        dialog_id: int | None = None,
        option_id: int | None = None,
    ) -> bool:
        """
        Проверяет условия для диалога или option.

        Должен быть передан только один из параметров:

            dialog_id
            или
            option_id

        Если для объекта условий нет — он считается доступным.

        Пример:

            await self.check_conditions(
                player_id=9,
                dialog_id=2,
            )
        """

        # Нельзя одновременно проверять dialog и option.
        if dialog_id is not None and option_id is not None:
            raise ValueError(
                "dialog_id and option_id cannot be specified together"
            )

        # Хотя бы один идентификатор должен быть указан.
        if dialog_id is None and option_id is None:
            raise ValueError(
                "Either dialog_id or option_id must be specified"
            )

        async with self.db.session_factory() as session:

            # Общие настройки загрузки условий.
            options = (
                selectinload(
                    Condition.condition_type
                ).selectinload(
                    ConditionType.allowed_operators
                )
            )

            # Получаем условия именно для указанного объекта.
            if dialog_id is not None:
                query = (
                    select(Condition)
                     .options(options)
                    .where(Condition.dialog_id == dialog_id)
                    .order_by(Condition.weight)
                )
            else:
                query = (
                    select(Condition)
                     .options(options)
                    .where(Condition.option_id == option_id)
                    .order_by(Condition.weight)
                )

            result = await session.execute(query)

            conditions = list(result.scalars())

            # Если условий нет — никаких ограничений нет.
            if not conditions:
                return True

            # Преобразуем плоский список из БД
            # в дерево условий.
            parser = ConditionParser(conditions)

            try:
                ast = parser.parse()
            except ConditionParseError:
                # Здесь можно добавить logging.exception(...)
                # если хочешь видеть ошибки конструктора
                # в логах.
                raise

            # Вычисляем получившееся дерево.
            return await self._evaluate_condition_expression(
                session=session,
                player_id=player_id,
                expression=ast,
            )


    async def _evaluate_condition_expression(
        self,
        session,
        player_id: int,
        expression: ConditionExpression,
    ) -> bool:
        """
        Рекурсивно вычисляет AST.

        Если expression — ConditionNode,
        вычисляется конкретное условие.

        Если expression — ConditionGroup,
        рекурсивно вычисляются все его children.
        """

        # --------------------------------------------
        # Обычное условие
        # --------------------------------------------

        if isinstance(expression, ConditionNode):
            return await self._evaluate_condition(
                session=session,
                player_id=player_id,
                condition=expression.condition,
            )

        # --------------------------------------------
        # Группа
        # --------------------------------------------

        if isinstance(expression, ConditionGroup):

            # Пустая группа не должна появляться после
            # нормального парсинга.
            if not expression.children:
                raise ConditionParseError(
                    "Cannot evaluate empty condition group"
                )

            # ----------------------------------------
            # AND
            # ----------------------------------------

            if expression.operator == LogicalOperator.AND:

                for child in expression.children:
                    result = await self._evaluate_condition_expression(
                        session=session,
                        player_id=player_id,
                        expression=child,
                    )

                    # Для AND достаточно одного False.
                    #
                    # Остальные условия можно не проверять.
                    if not result:
                        return False

                return True

            # ----------------------------------------
            # OR
            # ----------------------------------------

            if expression.operator == LogicalOperator.OR:

                for child in expression.children:
                    result = await self._evaluate_condition_expression(
                        session=session,
                        player_id=player_id,
                        expression=child,
                    )

                    # Для OR достаточно одного True.
                    if result:
                        return True

                return False

            raise ConditionParseError(
                f"Unknown logical operator: "
                f"{expression.operator}"
            )

        raise ConditionParseError(
            f"Unknown condition expression: "
            f"{type(expression).__name__}"
        )

    # Вычисляет конкретное условие.
    async def _evaluate_condition(
        self,
        session,
        player_id: int,
        condition: Condition,
    ) -> bool:

        # Проверяем, разрешён ли оператор для данного типа.
        allowed_operator_ids = {
            item.operator_type_id
            for item in condition.condition_type.allowed_operators
        }

        if condition.operator_type_id is None:
            if allowed_operator_ids:
                raise ConditionParseError(
                    f"Condition with id {condition.id}: "
                    f"operator_type_id is required for "
                    f"condition_type_id="
                    f"{condition.condition_type_id}"
                )

        elif condition.operator_type_id not in allowed_operator_ids:
            raise ConditionParseError(
                f"Condition with id {condition.id}: "
                f"operator_type_id="
                f"{condition.operator_type_id} "
                f"is not allowed for "
                f"condition_type_id="
                f"{condition.condition_type_id}"
            )

        #   В диалоге <value1> была выбрана опция <value2>
        if condition.condition_type_id == 3:
        
            if condition.value1 is None:
                raise ConditionParseError(
                    f"Condition with id {condition.id} "
                    f"requires value1"
                )
                
            if condition.value2 is None:
                raise ConditionParseError(
                    f"Condition with id {condition.id} "
                    f"requires value2"
                )

            # value в БД хранится как TEXT, поэтому преобразуем его в int.
            target_dialog_id = self._condition_value_to_int(
                condition=condition,
                value=condition.value1,
                value_name="value1",
            )
            
            target_option_id = self._condition_value_to_int(
                condition=condition,
                value=condition.value2,
                value_name="value2",
            )

            # Проверяем, есть ли у пользователя запись о выборе такой опции в этом диалоге.
            result = await session.execute(
                select(PlayerDialogChoice.id)
                .where(
                    PlayerDialogChoice.player_id == player_id,
                    PlayerDialogChoice.dialog_id == target_dialog_id,
                    PlayerDialogChoice.option_id == target_option_id,
                )
                .limit(1)
            )

            choice_exists = (
                result.scalar_one_or_none() is not None
            )

            if condition.operator_type_id == 1:
                return choice_exists

            if condition.operator_type_id == 2:
                return not choice_exists

            # Для <= и >= пока нет определённой
            # семантики для boolean-состояния
            raise ConditionParseError(
                f"Condition with id {condition.id}: "
                f"operator_type_id={condition.operator_type_id} "
                f"is not supported for "
                f"condition_type_id=4"
            )
        
        #   Диалог с id=<value1> пройден        
        elif condition.condition_type_id == 4:

            # Для этого типа value1 обязателен.
            #
            # Например:
            #
            # value1 = "123"
            #
            # означает:
            #
            # dialog 123 completed
            if condition.value1 is None:
                raise ConditionParseError(
                    f"Condition {condition.id} "
                    f"requires value1"
                )

            # value1 в БД хранится как TEXT,
            # поэтому преобразуем его в int.
            target_dialog_id = self._condition_value_to_int(
                condition=condition,
                value=condition.value1,
                value_name="value1",
            )

            # Проверяем, есть ли у пользователя
            # запись о прохождении этого диалога.
            #
            # Нам нужен только факт существования записи,
            # поэтому выбираем только ID и ограничиваем
            # результат одной строкой.
            result = await session.execute(
                select(PlayerDialogChoice.id)
                .where(
                    PlayerDialogChoice.player_id == player_id,
                    PlayerDialogChoice.dialog_id == target_dialog_id,
                )
                .limit(1)
            )

            dialog_completed = (
                result.scalar_one_or_none() is not None
            )

            # ==============================================
            # operator_type_id = 1
            #
            # =
            #
            # dialog completed == True
            # ==============================================

            if condition.operator_type_id == 1:
                return dialog_completed

            # ==============================================
            # operator_type_id = 2
            #
            # <>
            #
            # dialog completed != True
            # ==============================================

            if condition.operator_type_id == 2:
                return not dialog_completed

            # Для <= и >= пока нет определённой
            # семантики для boolean-состояния
            # "dialog completed".
            raise ConditionParseError(
                f"Condition {condition.id}: "
                f"operator_type_id={condition.operator_type_id} "
                f"is not supported for "
                f"condition_type_id=4"
            )

        # Другие типы пока специально не поддерживаем.
        raise ConditionParseError(
            f"Unsupported condition_type_id="
            f"{condition.condition_type_id} "
            f"(condition_id={condition.id})"
        )
        
    def _condition_value_to_int(
        self,
        condition: Condition,
        value: str | None,
        value_name: str,
    ) -> int:
        """
        Преобразует значение условия из TEXT в int.

        Например:

            value1 = "123"
            value_name = "value1"

        Если значение отсутствует или не является числом,
        выбрасывается ConditionParseError.
        """

        if value is None:
            raise ConditionParseError(
                f"Condition with id {condition.id} "
                f"requires {value_name}"
            )

        try:
            return int(value)
        except ValueError as exc:
            raise ConditionParseError(
                f"Condition with id {condition.id}: "
                f"{value_name} must be an integer, "
                f"got {value!r}"
            ) from exc
