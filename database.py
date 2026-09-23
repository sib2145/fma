from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from models.text import Text


class Database:
    def __init__(self, db_path: str):
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,
        )

        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def close(self):
        await self.engine.dispose()

    async def GetLocaleText(
        self,
        id: int,
        locale_id: int = 1
    ):
        async with self.session_factory() as session:
            text = await session.get(Text, (id, locale_id))

            if text is None:
                return None

            return text.text
