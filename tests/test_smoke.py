import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from demo_mode import DemoMode
from editor import EditorMode
from main import MenuScreen, PuzzleSelectScreen, SolveHistoryScreen
from play_mode import PlayMode
from storage import load_puzzle_library
from ui import WINDOW_HEIGHT, WINDOW_WIDTH, create_fonts


def test_screen_objects_initialize_and_draw() -> None:
    pygame.init()
    fonts = create_fonts()
    board = load_puzzle_library()[0]

    screens = [
        MenuScreen(),
        SolveHistoryScreen(),
        PuzzleSelectScreen("play"),
        PlayMode(board, board.metadata["id"], board.metadata["name"]),
        DemoMode(board, board.metadata["name"]),
        EditorMode(),
    ]

    for size in ((WINDOW_WIDTH, WINDOW_HEIGHT), (960, 900), (1440, 900)):
        surface = pygame.display.set_mode(size)
        for screen in screens:
            screen.update(0.016)
            screen.draw(surface, fonts)

    pygame.quit()
