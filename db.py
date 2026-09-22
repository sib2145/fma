import aiosqlite

class Db:
    def __init__(self):
        self.DB_PATH = "data/db.db"
        
    async def GetLocaleText(code, locale_code = 1):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                "SELECT `text` FROM `texts` WHERE `code` = ? and `locale_code` = ?",
                (code,locale_code,),
            )

            return await cursor.fetchone()