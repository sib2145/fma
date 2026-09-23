import asyncio

from instances.db import db

class Game:
    def __init__(self):
        self.is_running = False
        print("Game init")

    async def run(self):
        print("Game running...")
        
        await db.connect();
        
        self.is_running = True

        while self.is_running:
            self.update()
            await asyncio.sleep(1)

    def update(self):
        print("Game updated тик")

    async def stop(self):
        await db.close();
        self.is_running = False
        print("Game stop")

    def handle_action(self, player_id, action, data=None):
        return f"Игрок {player_id} сделал действие: {action}"
        
    async def register_account(self, telegram_id, locale_id = 1):
        return await db.Execute("INSERT INTO `players`(telegram_id, locale_id) VALUES(?, ?)", (telegram_id, locale_id))
