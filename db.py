import aiosqlite


class Db:
    def __init__(self):
        self.DB_PATH = "data/db.db"
        self.db = None

    async def connect(self):
        self.db = await aiosqlite.connect(self.DB_PATH)
        self.db.row_factory = aiosqlite.Row

    async def close(self):
        if self.db:
            await self.db.close()

    async def GetLocaleText(self, id, locale_id=1):
        cursor = await self.db.execute(
            "SELECT `text` FROM `texts` WHERE `id` = ? AND `locale_id` = ?",
            (id, locale_id),
        )

        row = await cursor.fetchone()
        return row[0]

    async def Execute(self, query, params=()):
        cursor = await self.db.execute(query, params)
        await self.db.commit()

        if query.strip().upper().startswith("INSERT"):
            return cursor.lastrowid

        return cursor.rowcount