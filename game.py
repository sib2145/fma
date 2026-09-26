import asyncio

from instances.db import db

from services.player import PlayerService
from services.text import TextService
from services.dialog import DialogService

class Game:
    def __init__(self):
        self.is_running = False
        
        self.players = PlayerService(db)
        self.texts = TextService(db)
        self.dialogs = DialogService(db, self.texts)
        
        print("Game init")

    async def run(self):
        print("Game engine running...")
        
        self.is_running = True
        
        print("Game engine run")

        while self.is_running:
            self.update()
            await asyncio.sleep(1)

    def update(self):
        pass
        #print("Game updated тик")

    async def stop(self):
        await db.close();
        self.is_running = False
        print("Game engine stopped")

    def handle_action(self, player_id, action, data=None):
        return f"Игрок {player_id} сделал действие: {action}"