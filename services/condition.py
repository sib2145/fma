from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias

from models.condition import Condition


# ID типов условий из таблицы condition_types.
CONDITION_TYPE_GROUP_BEGIN = 1
CONDITION_TYPE_GROUP_END = 2
CONDITION_TYPE_DIALOG_COMPLETED = 4
CONDITION_TYPE_OR = 5


class LogicalOperator(str, Enum):
    """
    Логический оператор группы условий.
    """

    AND = "and"
    OR = "or"


@dataclass
class ConditionNode:
    """
    Лист AST.

    Здесь находится обычное условие из таблицы conditions.

    Например:

        condition_type_id = 4
        value1 = "123"

    означает:

        dialog 123 completed
    """

    condition: Condition


@dataclass
class ConditionGroup:
    """
    Группа логических выражений.

    Примеры:

        AND(A, B)

        OR(A, B)

        AND(
            OR(A, B),
            C,
        )

    Благодаря этому группы могут быть вложенными.
    """

    operator: LogicalOperator = LogicalOperator.AND

    children: list["ConditionExpression"] = field(
        default_factory=list
    )


ConditionExpression: TypeAlias = ConditionNode | ConditionGroup


class ConditionParseError(Exception):
    """
    Ошибка структуры условий.

    Например:

    - незакрытая group begin;
    - group end без group begin;
    - OR в неправильном месте;
    - пустая группа.
    """

    pass


class ConditionParser:
    """
    Преобразует плоский список Condition в AST.

    В БД условия хранятся последовательно:

        weight | type
        -------+------
        1      | A
        2      | OR
        3      | B
        4      | C

    Parser превращает это в:

        AND(
            OR(A, B),
            C,
        )

    То есть отсутствие OR автоматически означает AND.
    """

    def __init__(self, conditions: list[Condition]):
        # На всякий случай сортируем здесь тоже.
        # Тогда parser не зависит от того, как именно
        # вызывающий код получил список из БД.
        self.conditions = sorted(
            conditions,
            key=lambda condition: condition.weight,
        )

        self.index = 0

    def parse(self) -> ConditionGroup:
        """
        Создаёт корневую группу AST.

        Корень всегда AND.

        Например:

            A B C

        превращается в:

            AND(A, B, C)
        """

        if not self.conditions:
            return ConditionGroup()

        root = self._parse_group(expect_end=False)

        # После разбора корневой группы не должно остаться
        # необработанных условий.
        if self.index != len(self.conditions):
            condition = self.conditions[self.index]

            raise ConditionParseError(
                f"Unexpected condition after root group: "
                f"id={condition.id}"
            )

        return root

    def _parse_group(
        self,
        expect_end: bool,
    ) -> ConditionGroup:
        """
        Читает условия до конца списка или до group end.

        expect_end=True означает, что текущая группа была
        открыта через group begin и обязательно должна
        закончиться group end.
        """

        # Сначала собираем последовательность элементов.

        parts: list[ConditionExpression | str] = []

        while self.index < len(self.conditions):
            condition = self.conditions[self.index]
            condition_type_id = condition.condition_type_id

            # --------------------------------------------
            # Конец текущей группы
            # --------------------------------------------

            if condition_type_id == CONDITION_TYPE_GROUP_END:
                if not expect_end:
                    raise ConditionParseError(
                        f"Unexpected group end: "
                        f"condition_id={condition.id}"
                    )

                self.index += 1

                return self._build_group(parts)

            # --------------------------------------------
            # Начало вложенной группы
            # --------------------------------------------

            if condition_type_id == CONDITION_TYPE_GROUP_BEGIN:
                self.index += 1

                nested_group = self._parse_group(
                    expect_end=True
                )

                parts.append(nested_group)

                continue

            # --------------------------------------------
            # OR
            # --------------------------------------------

            if condition_type_id == CONDITION_TYPE_OR:
                # OR не может быть первым элементом.
                if not parts:
                    raise ConditionParseError(
                        f"OR cannot be the first element: "
                        f"condition_id={condition.id}"
                    )

                # Сохраняем OR как оператор между элементами.
                parts.append("OR")

                self.index += 1

                continue

            # --------------------------------------------
            # Обычное условие
            # --------------------------------------------

            parts.append(
                ConditionNode(
                    condition=condition,
                )
            )

            self.index += 1

        # Если мы разбирали вложенную группу, а group end
        # так и не встретился — структура БД неправильная.
        if expect_end:
            raise ConditionParseError(
                "Group begin has no matching group end"
            )

        return self._build_group(parts)

    def _build_group(
        self,
        parts: list[ConditionExpression | str],
    ) -> ConditionGroup:
        """
        Преобразует последовательность элементов в AST.

        Правила:

            A B C
            ->
            AND(A, B, C)


            A OR B
            ->
            OR(A, B)


            A OR B OR C
            ->
            OR(A, B, C)


            A OR B C
            ->
            AND(
                OR(A, B),
                C,
            )


            A B OR C
            ->
            AND(
                A,
                OR(B, C),
            )


            A OR B C OR D
            ->
            AND(
                OR(A, B),
                OR(C, D),
            )

        То есть OR объединяет соседние выражения,
        а отсутствие OR между выражениями означает AND.
        """

        if not parts:
            raise ConditionParseError(
                "Condition group cannot be empty"
            )

        # Здесь будем хранить элементы верхнего уровня AND.
        #
        # Например:
        #
        # A OR B C
        #
        # превратится в:
        #
        # [
        #     OR(A, B),
        #     C,
        # ]
        and_children: list[ConditionExpression] = []

        # Текущая последовательность, соединённая OR.
        #
        # Например:
        #
        # A OR B OR C
        #
        # здесь постепенно будет:
        #
        # [A]
        # [A, B]
        # [A, B, C]
        current_or_group: list[ConditionExpression] = []

        index = 0

        while index < len(parts):
            part = parts[index]

            # OR сам по себе ничего не добавляет в AST.
            # Он говорит, что СЛЕДУЮЩИЙ элемент нужно
            # присоединить к текущей OR-группе.
            if part == "OR":
                # OR не может быть первым элементом.
                if not current_or_group:
                    raise ConditionParseError(
                        "OR cannot appear without "
                        "a previous expression"
                    )

                # После OR обязательно должен быть
                # следующий expression.
                if index + 1 >= len(parts):
                    raise ConditionParseError(
                        "OR cannot be the last element"
                    )

                next_part = parts[index + 1]

                # Следующий элемент не может снова быть OR.
                if next_part == "OR":
                    raise ConditionParseError(
                        "Two OR operators cannot appear "
                        "consecutively"
                    )

                # Добавляем следующий элемент
                # в текущую OR-группу.
                current_or_group.append(next_part)

                index += 2

                continue

            # Если current_or_group уже содержит элементы,
            # значит перед нами новый элемент без OR.
            #
            # Например:
            #
            # A OR B C
            #
            # Мы дошли до C, поэтому сначала завершаем
            # OR(A, B), а затем начинаем новую AND-часть.
            if current_or_group:
                if len(current_or_group) == 1:
                    # Просто A
                    and_children.append(
                        current_or_group[0]
                    )
                else:
                    # A OR B OR C
                    and_children.append(
                        ConditionGroup(
                            operator=LogicalOperator.OR,
                            children=current_or_group,
                        )
                    )

                current_or_group = []

            # Начинаем новую OR-последовательность.
            current_or_group.append(part)

            index += 1

        # Добавляем последнюю OR-группу.
        if current_or_group:
            if len(current_or_group) == 1:
                and_children.append(
                    current_or_group[0]
                )
            else:
                and_children.append(
                    ConditionGroup(
                        operator=LogicalOperator.OR,
                        children=current_or_group,
                    )
                )

        # Верхний уровень всегда AND.
        #
        # Даже если здесь всего один элемент:
        #
        # OR(A, B)
        #
        # получится:
        #
        # AND(
        #     OR(A, B)
        # )
        #
        # Это нормально: лишний уровень не влияет
        # на результат и сильно упрощает parser.

        return ConditionGroup(
            operator=LogicalOperator.AND,
            children=and_children,
        )