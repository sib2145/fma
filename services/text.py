from sqlalchemy import func, select

from models.text import Text


class TextService:
    def __init__(self, db):
        self.db = db

    async def get_next_id(self, session) -> int:
        result = await session.execute(
            select(func.max(Text.id))
        )

        max_id = result.scalar_one()

        return (max_id or 0) + 1

    async def create(
        self,
        session,
        text: str,
        locale_id: int = 1
    ) -> Text:
        text_id = await self.get_next_id(session)

        text_model = Text(
            id=text_id,
            locale_id=locale_id,
            text=text
        )

        session.add(text_model)
        await session.flush()

        return text_model

    async def update(
        self,
        text_id: int,
        text: str,
        locale_id: int = 1
    ) -> bool:
        async with self.db.session_factory() as session:
            result = await session.execute(
                select(Text)
                .where(
                    Text.id == text_id,
                    Text.locale_id == locale_id
                )
            )

            text_model = result.scalar_one_or_none()

            if text_model is None:
                return False

            text_model.text = text

            await session.commit()

            return True
