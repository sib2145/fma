import asyncio


class Game:
    def __init__(self):
        self.is_running = False
        print("Game init")

    async def run(self):
        self.is_running = True
        
        print("Game running...")

        while self.is_running:
            self.update()
            await asyncio.sleep(1)

    def update(self):
        print("Game updated тик")

    def stop(self):
        self.is_running = False
        print("Game stop")

    def handle_action(self, player_id, action, data=None):
        return f"Игрок {player_id} сделал действие: {action}"
