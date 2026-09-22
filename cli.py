import asyncio

from game import Game


async def main():
    game = Game()

    # Гарантированно выполняем первый update
    game.update()

    # Запускаем игровой цикл
    game_task = asyncio.create_task(game.run())

    result = game.handle_action(
        player_id=1,
        action="test",
    )

    print(result)

    game.stop()

    await game_task


if __name__ == "__main__":
    asyncio.run(main())