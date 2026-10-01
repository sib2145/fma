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

from views.dialog_session import DialogSession

from sqlalchemy import delete

from models.player import Player


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
    async def on_open_dialog_processor(
        self,
        session: DialogSession,
    ) -> DialogSession:
        """
        Срабатывает при открытии диалога.

        Processor получает всю сессию пользователя и может
        изменять dialog и processor_data.
        """

        dialog = session.dialog

        if dialog is None:
            return session

        print(
            "open dialog processor, id: ",
            dialog.id,
        )

        print(
            "open dialog processor data: ",
            session.processor_data,
        )

        # --------------------------------------------------
        # Получаем последнее выбранное действие.
        #
        # Оно было записано Telegram handler'ом перед
        # вызовом on_close.
        #
        # pop() нужен, чтобы одно событие не обработалось
        # повторно при следующем открытии.
        # --------------------------------------------------

        selected_option = session.processor_data.pop(
            "selected_option",
            None,
        )

        if selected_option is not None:
            print(
                "selected option:",
                selected_option.id,
                selected_option.processor_flag,
            )

        # --------------------------------------------------
        # Редактор диалогов - просмотр диалога
        # --------------------------------------------------

        if dialog.id == 6:
            viewed_dialog = session.processor_data.get(
                "viewing_dialog"
            )

            if viewed_dialog is not None:
                dialog.template_context.update({
                    "dialog": viewed_dialog,
                })

        # --------------------------------------------------
        # Редактор диалогов - главная страница
        # --------------------------------------------------

        elif dialog.id == 7:
            dialogs_count = await self.count()

            dialog.template_context[
                "dialogs_count"
            ] = dialogs_count

        # --------------------------------------------------
        # Редактор диалогов - список диалогов
        # --------------------------------------------------

        elif dialog.id == 10:
            import math

            dialogs_count = await self.count()

            pages_count = max(
                1,
                math.ceil(
                    dialogs_count / self.dialogs_per_page
                ),
            )

            # Получаем текущую страницу из session.
            page = session.processor_data.get(
                "page",
                1,
            )

            try:
                page = int(page)
            except (TypeError, ValueError):
                page = 1

            # --------------------------------------------------
            # Обрабатываем выбранную динамическую кнопку.
            #
            # Здесь больше НЕТ option_index.
            # --------------------------------------------------

            if selected_option is not None:

                if (
                    selected_option.processor_flag
                    == "previous_page"
                ):
                    page -= 1

                elif (
                    selected_option.processor_flag
                    == "next_page"
                ):
                    page += 1

            # Ограничиваем страницу допустимым диапазоном.
            page = max(
                1,
                min(page, pages_count),
            )

            session.processor_data[
                "page"
            ] = page

            dialogs = await self.get_page(
                page=page,
                per_page=self.dialogs_per_page,
            )

            dialog.options.clear()

            # --------------------------------------------------
            # Кнопки диалогов.
            # --------------------------------------------------

            for item in dialogs:
                option = await self._create_dynamic_option(
                    dialog_id=dialog.id,
                    text=(
                        f"{item.id}. "
                        f"{item.comment or item.text.text}"
                    ),
                    next_dialog_id=item.id,
                    processor_flag="open_dialog",
                )

                dialog.options.append(option)

            # --------------------------------------------------
            # Кнопка "Назад".
            # --------------------------------------------------

            if page > 1:
                dialog.options.append(
                    await self._create_dynamic_option(
                        dialog_id=dialog.id,
                        text="◀ Назад",
                        next_dialog_id=dialog.id,
                        processor_flag="previous_page",
                    )
                )

            # --------------------------------------------------
            # Кнопка "Вперёд".
            # --------------------------------------------------

            if page < pages_count:
                dialog.options.append(
                    await self._create_dynamic_option(
                        dialog_id=dialog.id,
                        text="Вперёд ▶",
                        next_dialog_id=dialog.id,
                        processor_flag="next_page",
                    )
                )

            dialog.template_context.update({
                "dialogs_count": dialogs_count,
                "dialog_list_page": page,
                "dialog_list_pages": pages_count,
                "dialogs_per_page": self.dialogs_per_page,
            })
            
        # --------------------------------------------------
        # Удаление диалога
        # --------------------------------------------------
        
        # --------------------------------------------------
        # Если confirmed не установлен, просто показываем
        # обычный диалог подтверждения.
        # --------------------------------------------------

        elif dialog.id == 13:

            confirmed = session.processor_data.pop(
                "confirmed",
                0,
            )

            if confirmed == 1:

                delete_dialog_id = (
                    session.processor_data.pop(
                        "delete_dialog_id",
                        None,
                    )
                )

                if delete_dialog_id is not None:

                    deleted = await self.delete(
                        delete_dialog_id
                    )

                    if deleted:

                        next_dialog = await self.get_by_id(
                            7
                        )

                        if next_dialog is not None:
                            session.dialog = next_dialog

                            # После удаления старый просмотренный
                            # DialogView больше не существует.
                            session.processor_data.pop(
                                "viewing_dialog",
                                None,
                            )

                    else:
                        print(
                            "Не удалось удалить диалог:",
                            delete_dialog_id,
                        )


        return session

    
    # Срабатывает, когда пользователь выбрал какую то опцию в диалоге
    async def on_close_dialog_processor(
        self,
        session: DialogSession,
    ) -> DialogSession:
        """
        Срабатывает после выбора пользователем опции,
        но до стандартной обработки этой опции.
        """

        dialog = session.dialog

        if dialog is None:
            return session

        print(
            "close dialog processor, id: ",
            dialog.id,
        )

        selected_option = session.processor_data.get(
            "selected_option"
        )

        if selected_option is not None:
            print(
                "close dialog selected option:",
                selected_option.id,
                selected_option.processor_flag,
            )

        # Редактор диалогов — просмотр диалога
        if dialog.id == 6:
            viewing_dialog = session.processor_data.get(
                "viewing_dialog"
            )

            if viewing_dialog is not None:
                # Кнопка "Установить себе и перейти"
                if selected_option.id == 62:
                    selected_option.next_dialog_id = (
                        viewing_dialog.id
                    )

                    selected_option.show_dialog_mode = (
                        2
                        if viewing_dialog.is_extra
                        else 1
                    )
                
                # Кнопка "редактировать текст"
                elif selected_option.id == 63:
                    session.processor_data["edit_dialog_id"] = viewing_dialog.id
                    
                # Кнопка удаления диалога
                elif selected_option.id == 74:
                    viewing_dialog = session.processor_data.get(
                        "viewing_dialog"
                    )

                    if viewing_dialog is not None:
                        session.processor_data[
                            "delete_dialog_id"
                        ] = viewing_dialog.id
                        

        if (
            dialog.id == 13
            and selected_option.id == 75
        ):
            session.processor_data[
                "confirmed"
            ] = 1



        return session

        
    # Срабатывает, когда пользователь ввёл что то после диалога, который спрашивает у пользователя ввод
    # Если функция вернула valid = True, то handler перебросит на указанный в базе следующий диалог (по его id). Иначе вернет в этот же за повторным вводом
    async def on_input_dialog_processor(
        self,
        session: DialogSession,
    ) -> tuple[
        bool,
        DialogSession,
        str | None,
    ]:
        """
        Срабатывает после пользовательского текстового ввода.

        Возвращает:
            valid
            session
            error_message
        """

        dialog = session.dialog

        if dialog is None:
            return (
                False,
                session,
                "Диалог не найден",
            )

        print(
            "input dialog processor, id: ",
            dialog.id,
        )

        user_input = session.user_input

        valid = True
        error_message = None

        # --------------------------------------------------
        # Ввод текста для добавления нового диалога в админке
        # --------------------------------------------------

        if dialog.id == 8:
            if (
                user_input != ""
                and user_input is not None
            ):
                dialog_id = await self.create(
                    text=user_input
                )

                created_dialog = await self.get_by_id(
                    dialog_id
                )

                session.processor_data[
                    "viewing_dialog"
                ] = created_dialog

            else:
                valid = False

        # --------------------------------------------------
        # Ввод id диалога для просмотра
        # --------------------------------------------------

        elif dialog.id == 9:
            try:
                dialog_id = int(user_input)
            except (TypeError, ValueError):
                valid = False

            if valid:
                viewed_dialog = await self.get_by_id(
                    dialog_id
                )

                if viewed_dialog is None:
                    valid = False
                else:
                    session.processor_data[
                        "viewing_dialog"
                    ] = viewed_dialog
        
        # Редактирование текста диалога
        elif dialog.id == 11:
            edit_dialog_id = session.processor_data.get("edit_dialog_id")

            if edit_dialog_id is None:
                error_message = "Не передан edit_dialog_id"
                valid = False

            target_dialog = await self.get_by_id(edit_dialog_id)

            if target_dialog is None:
                error_message = "Редактируемый диалог не найден"
                valid = False

            if valid:
                await self.text_service.update(
                    text_id=target_dialog.text_id,
                    text=user_input
                )
                
                session.processor_data.pop("edit_dialog_id")
                viewed_dialog = session.processor_data.get("viewing_dialog")
                viewed_dialog.text.template = user_input
                viewed_dialog.text.text = user_input
            
            

        return (
            valid,
            session,
            error_message,
        )


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

            processor_flag=None,
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


    async def delete(
        self,
        dialog_id: int,
    ) -> bool:
        """
        Удаляет диалог и связанные с ним данные.

        Перед удалением:
        - отвязывает другие кнопки, ведущие на этот диалог;
        - очищает текущий диалог игроков;
        - удаляет сохранённые выборы;
        - удаляет условия;
        - удаляет кнопки диалога;
        - удаляет сам диалог.

        Тексты удаляются только в том случае, если они
        больше нигде не используются.
        """

        async with self.db.session_factory() as session:

            # --------------------------------------------------
            # Проверяем существование диалога.
            # --------------------------------------------------

            dialog = await session.get(
                Dialog,
                dialog_id,
            )

            if dialog is None:
                return False

            # --------------------------------------------------
            # Получаем кнопки удаляемого диалога.
            #
            # Нам понадобятся их id и text_id.
            # --------------------------------------------------

            result = await session.execute(
                select(DialogOption).where(
                    DialogOption.dialog_id == dialog_id
                )
            )

            options = list(result.scalars())

            option_ids = [
                option.id
                for option in options
            ]

            option_text_ids = [
                option.text_id
                for option in options
            ]

            dialog_text_id = dialog.text_id

            # --------------------------------------------------
            # Другие кнопки могут вести на удаляемый диалог.
            #
            # После удаления они должны просто перестать
            # иметь следующий диалог.
            # --------------------------------------------------

            result = await session.execute(
                select(DialogOption).where(
                    DialogOption.next_dialog_id
                    == dialog_id
                )
            )

            linked_options = list(result.scalars())

            for option in linked_options:
                option.next_dialog_id = None

            # --------------------------------------------------
            # Игроки могут находиться в удаляемом диалоге.
            #
            # Чтобы после удаления у них не осталось
            # ссылки на несуществующий диалог.
            # --------------------------------------------------

            result = await session.execute(
                select(Player).where(
                    (Player.current_dialog_id == dialog_id)
                    | (
                        Player.current_extra_dialog_id
                        == dialog_id
                    )
                )
            )

            players = list(result.scalars())

            for player in players:

                if player.current_dialog_id == dialog_id:
                    player.current_dialog_id = None

                if (
                    player.current_extra_dialog_id
                    == dialog_id
                ):
                    player.current_extra_dialog_id = None

            # --------------------------------------------------
            # Удаляем сохранённые выборы игроков,
            # связанные с удаляемым диалогом.
            # --------------------------------------------------

            await session.execute(
                delete(PlayerDialogChoice).where(
                    PlayerDialogChoice.dialog_id
                    == dialog_id
                )
            )

            # --------------------------------------------------
            # Удаляем условия самого диалога.
            # --------------------------------------------------

            await session.execute(
                delete(Condition).where(
                    Condition.dialog_id == dialog_id
                )
            )

            # --------------------------------------------------
            # Удаляем условия кнопок.
            # --------------------------------------------------

            if option_ids:
                await session.execute(
                    delete(Condition).where(
                        Condition.option_id.in_(
                            option_ids
                        )
                    )
                )

            # --------------------------------------------------
            # Удаляем кнопки.
            # --------------------------------------------------

            if option_ids:
                await session.execute(
                    delete(DialogOption).where(
                        DialogOption.id.in_(
                            option_ids
                        )
                    )
                )

            # --------------------------------------------------
            # Удаляем сам диалог.
            # --------------------------------------------------

            await session.delete(dialog)

            await session.flush()

            # --------------------------------------------------
            # Удаляем тексты кнопок и самого диалога,
            # только если они больше нигде не используются.
            #
            # Это важно, потому что один Text теоретически
            # может быть связан с несколькими объектами.
            # --------------------------------------------------

            text_ids = set(
                option_text_ids
            )

            text_ids.add(dialog_text_id)

            for text_id in text_ids:

                # Текст всё ещё используется диалогом?
                result = await session.execute(
                    select(Dialog.id)
                    .where(
                        Dialog.text_id == text_id
                    )
                    .limit(1)
                )

                if result.scalar_one_or_none() is not None:
                    continue

                # Текст всё ещё используется кнопкой?
                result = await session.execute(
                    select(DialogOption.id)
                    .where(
                        DialogOption.text_id
                        == text_id
                    )
                    .limit(1)
                )

                if result.scalar_one_or_none() is not None:
                    continue

                await session.execute(
                    delete(Text).where(
                        Text.id == text_id
                    )
                )

            await session.commit()

            return True
