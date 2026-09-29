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

import math

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

from views.dialog import (
    DialogView,
    DialogOptionView,
)

class DialogService:
    def __init__(
        self,
        db,
        text_service,
        show_extra=False,
        dialogs_per_page=10,
    ):
        self.db = db
        self.text_service = text_service

        self.show_extra = show_extra
        self.dialogs_per_page = dialogs_per_page


    
    # Срабатывает, когда пользователю показан диалог. Служит для предварительной обработки и замены значений
    async def on_open_dialog_processor(self, triggered_dialog, params):
        print("open dialog processor, id: ", triggered_dialog.id)
        print("open dialog processor params: ", params)
        
        # Редактор диалогов - просмотр диалога
        if triggered_dialog.id == 6:
            #dialog = params.pop("dialog", None)
            dialog = params.get("dialog", None)
            
            if triggered_dialog is not None:
                triggered_dialog.template_context.update({
                    "dialog": dialog,
                })
            
        
        # Редактор диалогов - главная страница
        elif triggered_dialog.id == 7:

            dialogs_count = await self.count()

            triggered_dialog.template_context["dialogs_count"] = dialogs_count
            
        # Редактор диалогов - список диалогов
        elif triggered_dialog.id == 10:
            import math

            dialogs_count = await self.count()

            pages_count = max(
                1,
                math.ceil(
                    dialogs_count / self.dialogs_per_page
                ),
            )

            page = params.get(
                "dialog_list_page",
                1,
            )

            try:
                page = int(page)
            except (TypeError, ValueError):
                page = 1

            page = max(
                1,
                min(page, pages_count),
            )

            params["dialog_list_page"] = page

            dialogs = await self.get_page(
                page=page,
                per_page=self.dialogs_per_page,
            )

            triggered_dialog.options.clear()

            # Кнопки диалогов.
            for dialog in dialogs:
                option = await self._create_dynamic_option(
                    dialog_id=triggered_dialog.id,
                    text=(
                        f"{dialog.id}. "
                        f"{dialog.comment or dialog.text.text}"
                    ),
                    next_dialog_id=dialog.id,
                    processor_flag="open_dialog",
                )

                triggered_dialog.options.append(option)

            # Назад.
            if page > 1:
                triggered_dialog.options.append(
                    await self._create_dynamic_option(
                        dialog_id=triggered_dialog.id,
                        text="◀ Назад",
                        next_dialog_id=triggered_dialog.id,
                        processor_flag="previous_page",
                    )
                )

            # Вперёд.
            if page < pages_count:
                triggered_dialog.options.append(
                    await self._create_dynamic_option(
                        dialog_id=triggered_dialog.id,
                        text="Вперёд ▶",
                        next_dialog_id=triggered_dialog.id,
                        processor_flag="next_page",
                    )
                )


            triggered_dialog.template_context.update({
                "dialogs_count": dialogs_count,
                "dialog_list_page": page,
                "dialog_list_pages": pages_count,
                "dialogs_per_page": self.dialogs_per_page,
            })



        
        return triggered_dialog, params   # Возвращаем обратно при необходимости модифицированный объект (для дальнейшей отрисовки и т.д.)
    
    # Срабатывает, когда пользователь выбрал какую то опцию в диалоге
    async def on_close_dialog_processor(
        self,
        triggered_dialog,
        option_selected,
        params,
        option_index=None,
    ):

        
        print("close dialog processor, id: ", triggered_dialog.id)
        
        # Редактор диалогов — просмотр диалога
        # "Установить себе и перейти"
        if (
            triggered_dialog.id == 6
            and option_selected is not None
            and option_selected.id == 62
        ):
            viewed_dialog = params.get("dialog")

            if viewed_dialog is not None:
                option_selected.next_dialog_id = viewed_dialog.id
                option_selected.show_dialog_mode = (
                    2 if viewed_dialog.is_extra else 1
                )
                
        # Редактор диалогов — список диалогов
        elif (
            triggered_dialog.id == 10
            and option_selected is not None
        ):
            selected_flag = option_selected.processor_flag

            if selected_flag == "previous_page":
                page = params.get(
                    "dialog_list_page",
                    1,
                )

                try:
                    page = int(page)
                except (TypeError, ValueError):
                    page = 1

                params["dialog_list_page"] = max(
                    1,
                    page - 1,
                )

            elif selected_flag == "next_page":
                dialogs_count = await self.count()

                pages_count = max(
                    1,
                    math.ceil(
                        dialogs_count / self.dialogs_per_page
                    ),
                )

                page = params.get(
                    "dialog_list_page",
                    1,
                )

                try:
                    page = int(page)
                except (TypeError, ValueError):
                    page = 1

                params["dialog_list_page"] = min(
                    page + 1,
                    pages_count,
                )


        
        return triggered_dialog, option_selected, params  # Возвращаем обратно при необходимости модифицированные объекты
        
    # Срабатывает, когда пользователь ввёл что то после диалога, который спрашивает у пользователя ввод
    async def on_input_dialog_processor(self, triggered_dialog, params, user_input):
        print("input dialog processor, id: ", triggered_dialog.id)
        valid = True
        error_message = None
        
        # Перехваты пользовательского ввода в диалогах по id диалога, и соответственно либо действия, либо просто валидация типов и ввода
        
        # Ввод текста для добавления нового диалога в админке
        if triggered_dialog.id == 8:
            if user_input != "" and user_input is not None:
                dialog_id = await self.create(
                    text=user_input
                )
                
                dialog = await self.get_by_id(dialog_id)
                
                params['dialog'] = dialog
            else:
                valid = False
        
        # Ввод id диалога для просмотра
        elif triggered_dialog.id == 9:
            try:
                dialog_id = int(user_input)
            except ValueError:
                valid = False
                
            if valid:
                dialog = await self.get_by_id(dialog_id)
                if dialog is None:
                    
                    valid = False
                else:
                    params['dialog'] = dialog
        
        return valid, triggered_dialog, params, user_input, error_message

    async def get_by_id(
        self,
        dialog_id: int
    ) -> DialogView | None:

        async with self.db.session_factory() as session:
            result = await session.execute(
                select(Dialog)
                .options(
                    selectinload(Dialog.text),

                    selectinload(Dialog.next_dialog)
                        .selectinload(Dialog.text),

                    selectinload(Dialog.options)
                        .selectinload(DialogOption.text),

                    selectinload(Dialog.options)
                        .selectinload(DialogOption.next_dialog)
                        .selectinload(Dialog.text),
                )
                .where(Dialog.id == dialog_id)
            )

            dialog = result.scalar_one_or_none()

            if dialog is None:
                return None

            dialog.options.sort(
                key=lambda option: option.weight or 0
            )

            return await self._create_dialog_view(
                dialog
            )



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
            query = select(
                func.count(Dialog.id)
            )

            if not self.show_extra:
                query = query.where(
                    Dialog.is_extra == 0
                )

            result = await session.execute(query)

            return result.scalar_one()


    async def get_page(
        self,
        page: int,
        per_page: int,
    ) -> list[Dialog]:

        async with self.db.session_factory() as session:
            offset = (page - 1) * per_page

            query = (
                select(Dialog)
                .options(
                    selectinload(Dialog.text)
                )
            )

            if not self.show_extra:
                query = query.where(
                    Dialog.is_extra == 0
                )

            query = (
                query
                .order_by(Dialog.id)
                .offset(offset)
                .limit(per_page)
            )

            result = await session.execute(query)

            return list(result.scalars())


    async def search(
        self,
        search_text: str,
        locale_id: int = 1,
    ) -> list[Dialog]:

        async with self.db.session_factory() as session:
            query = (
                select(Dialog)
                .join(
                    Text,
                    Dialog.text_id == Text.id
                )
                .options(
                    selectinload(Dialog.text)
                )
                .where(
                    Text.locale_id == locale_id,
                    Text.text.ilike(
                        f"%{search_text}%"
                    ),
                )
                .order_by(Dialog.id)
            )

            if not self.show_extra:
                query = query.where(
                    Dialog.is_extra == 0
                )

            result = await session.execute(query)

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


    async def _create_text_view(
        self,
        text
    ):
        if text is None:
            return None

        return await self.text_service.create_view(text)

    async def _create_option_view(
        self,
        option
    ) -> DialogOptionView:

        next_dialog_text = None

        if option.next_dialog is not None:
            next_dialog_text = await self.text_service.create_view(
                option.next_dialog.text
            )

        return DialogOptionView(
            id=option.id,
            dialog_id=option.dialog_id,
            condition=option.condition,
            weight=option.weight,
            text=await self.text_service.create_view(
                option.text
            ),
            next_dialog_id=option.next_dialog_id,
            next_dialog_text=next_dialog_text,
            show_dialog_mode=option.show_dialog_mode,
            save_choice=option.save_choice,
        )

    async def _create_dialog_view(
        self,
        dialog
    ) -> DialogView:

        next_dialog_text = None
        next_dialog_comment = None

        if dialog.next_dialog is not None:
            next_dialog_text = await self.text_service.create_view(
                dialog.next_dialog.text
            )
            
            next_dialog_comment = dialog.next_dialog.comment
            

        options = [
            await self._create_option_view(option)
            for option in dialog.options
        ]

        return DialogView(
            id=dialog.id,
            text_id=dialog.text_id,
            text=await self.text_service.create_view(
                dialog.text
            ),
            image=dialog.image,
            next_dialog_id=dialog.next_dialog_id,
            next_dialog_comment=next_dialog_comment,
            next_dialog_text=next_dialog_text,
            save_choice=dialog.save_choice,
            multiselect=dialog.multiselect,
            is_extra=dialog.is_extra,
            input_type=dialog.input_type,
            comment=dialog.comment,
            options=options,
        )

    def build_template_context(
        self,
        dialog: DialogView
    ) -> dict:

        context = {
            #"dialog_id": dialog.id,
            #"dialog_comment": dialog.comment,
            #"buttons_count": len(dialog.options),
            #"next_dialog_id": dialog.next_dialog_id,
            #"next_dialog_text": (
            #    dialog.next_dialog_text.text
            #    if dialog.next_dialog_text is not None
            #    else None
            #),
        }

        context.update(
            dialog.template_context
        )

        return context

    async def render_view(
        self,
        dialog: DialogView
    ) -> DialogView:

        template_context = self.build_template_context(
            dialog
        )

        await self.text_service.render_view(
            dialog.text,
            template_context
        )

        for option in dialog.options:
            await self.text_service.render_view(
                option.text,
                template_context
            )

        #    if option.next_dialog_text is not None:
        #        await self.text_service.render_view(
        #            option.next_dialog_text,
        #            template_context
        #        )

        #if dialog.next_dialog_text is not None:
        #    await self.text_service.render_view(
        #        dialog.next_dialog_text,
        #        template_context
        #    )

        return dialog


    async def _create_dynamic_option(
        self,
        dialog_id: int,
        text: str,
        next_dialog_id: int | None,
        processor_flag: str | None = None,
    ) -> DialogOptionView:

        from views.text import TextView

        return DialogOptionView(
            id=None,
            dialog_id=dialog_id,
            condition=None,
            weight=None,

            text=TextView(
                id=None,
                locale_id=1,
                template=text,
                text=text,
            ),

            next_dialog_id=next_dialog_id,
            next_dialog_text=None,

            show_dialog_mode=None,
            save_choice=False,

            processor_flag=processor_flag,
        )
