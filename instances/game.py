# Глобальные экземпляры классов и т.д.

from game import Game
from config import config

SHOW_EXTRA = config.getboolean(
    "dialog",
    "show_extra",
    fallback=False,
)

game = Game(
    show_extra=SHOW_EXTRA
)