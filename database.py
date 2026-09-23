from sqlalchemy import select, event
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
            #echo=False,
            echo=True,
        )

        @event.listens_for(self.engine.sync_engine, "connect")
        def configure_sqlite(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()

            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")

            cursor.close()

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
