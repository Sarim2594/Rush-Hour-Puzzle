from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from board import Board, GRID_SIZE, Move


WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 760
BOARD_ORIGIN = (60, 90)
CELL_SIZE = 88
BOARD_PIXELS = GRID_SIZE * CELL_SIZE
PANEL_X = BOARD_ORIGIN[0] + BOARD_PIXELS + 40

BACKGROUND = (243, 238, 229)
PANEL_BG = (249, 247, 241)
GRID_LIGHT = (236, 229, 214)
GRID_DARK = (197, 189, 170)
TEXT = (44, 41, 34)
MUTED = (113, 103, 84)
ACCENT = (198, 102, 71)
ACCENT_DARK = (141, 69, 45)
SUCCESS = (66, 137, 95)
WARNING = (190, 141, 55)
HINT = (33, 106, 146)
RED_CAR = (210, 65, 51)
WHITE = (255, 255, 255)


VEHICLE_PALETTE = [
    (61, 102, 168),
    (86, 150, 109),
    (189, 130, 52),
    (110, 88, 166),
    (70, 145, 148),
    (180, 95, 111),
    (145, 125, 76),
    (83, 118, 92),
]


def create_fonts() -> dict[str, pygame.font.Font]:
    return {
        "title": pygame.font.SysFont("georgia", 34, bold=True),
        "heading": pygame.font.SysFont("georgia", 24, bold=True),
        "body": pygame.font.SysFont("segoeui", 22),
        "small": pygame.font.SysFont("segoeui", 18),
        "button": pygame.font.SysFont("segoeui", 22, bold=True),
    }


def board_rect() -> pygame.Rect:
    return pygame.Rect(BOARD_ORIGIN[0], BOARD_ORIGIN[1], BOARD_PIXELS, BOARD_PIXELS)


def cell_rect(row: int, col: int) -> pygame.Rect:
    return pygame.Rect(
        BOARD_ORIGIN[0] + col * CELL_SIZE,
        BOARD_ORIGIN[1] + row * CELL_SIZE,
        CELL_SIZE,
        CELL_SIZE,
    )


def screen_to_cell(position: tuple[int, int]) -> tuple[int, int] | None:
    if not board_rect().collidepoint(position):
        return None
    x, y = position
    col = (x - BOARD_ORIGIN[0]) // CELL_SIZE
    row = (y - BOARD_ORIGIN[1]) // CELL_SIZE
    if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
        return int(row), int(col)
    return None


def vehicle_color(vehicle_id: str, is_red: bool) -> tuple[int, int, int]:
    if is_red:
        return RED_CAR
    index = sum(ord(char) for char in vehicle_id) % len(VEHICLE_PALETTE)
    return VEHICLE_PALETTE[index]


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    position: tuple[int, int],
) -> None:
    rendered = font.render(text, True, color)
    surface.blit(rendered, position)


@dataclass(slots=True)
class Button:
    label: str
    rect: pygame.Rect
    action: str
    fill: tuple[int, int, int] = ACCENT
    text_color: tuple[int, int, int] = WHITE

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font], mouse_pos: tuple[int, int]) -> None:
        hovered = self.rect.collidepoint(mouse_pos)
        color = tuple(max(0, channel - 16) for channel in self.fill) if hovered else self.fill
        pygame.draw.rect(surface, color, self.rect, border_radius=14)
        pygame.draw.rect(surface, ACCENT_DARK, self.rect, width=2, border_radius=14)
        rendered = fonts["button"].render(self.label, True, self.text_color)
        surface.blit(rendered, rendered.get_rect(center=self.rect.center))

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            return self.action
        return None


def make_button_row(labels: list[tuple[str, str]], x: int, y: int, width: int = 150, gap: int = 12) -> list[Button]:
    buttons: list[Button] = []
    for index, (label, action) in enumerate(labels):
        rect = pygame.Rect(x + index * (width + gap), y, width, 48)
        buttons.append(Button(label=label, rect=rect, action=action))
    return buttons


def panel_card(surface: pygame.Surface, rect: pygame.Rect) -> None:
    pygame.draw.rect(surface, PANEL_BG, rect, border_radius=18)
    pygame.draw.rect(surface, GRID_DARK, rect, width=2, border_radius=18)


def draw_board(
    surface: pygame.Surface,
    board: Board,
    fonts: dict[str, pygame.font.Font],
    *,
    selected_vehicle_id: str | None = None,
    hint_move: Move | None = None,
) -> dict[str, pygame.Rect]:
    rects: dict[str, pygame.Rect] = {}
    grid_rect = board_rect()
    pygame.draw.rect(surface, WHITE, grid_rect, border_radius=20)
    pygame.draw.rect(surface, GRID_DARK, grid_rect, width=3, border_radius=20)

    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            cell = cell_rect(row, col)
            color = GRID_LIGHT if (row + col) % 2 == 0 else BACKGROUND
            pygame.draw.rect(surface, color, cell.inflate(-4, -4), border_radius=12)

    exit_cell = cell_rect(board.red_vehicle.row, GRID_SIZE - 1)
    exit_marker = pygame.Rect(exit_cell.right - 12, exit_cell.top + 12, 24, exit_cell.height - 24)
    pygame.draw.rect(surface, SUCCESS, exit_marker, border_radius=10)

    hint_vehicle_id = hint_move.vehicle_id if hint_move else None
    for vehicle in board.vehicles:
        start_cell = cell_rect(vehicle.row, vehicle.col)
        width = vehicle.length * CELL_SIZE if vehicle.orientation == "H" else CELL_SIZE
        height = CELL_SIZE if vehicle.orientation == "H" else vehicle.length * CELL_SIZE
        vehicle_rect = pygame.Rect(start_cell.x + 6, start_cell.y + 6, width - 12, height - 12)
        rects[vehicle.id] = vehicle_rect

        fill = vehicle_color(vehicle.id, vehicle.is_red)
        border_color = ACCENT_DARK
        if vehicle.id == selected_vehicle_id:
            pygame.draw.rect(surface, HINT, vehicle_rect.inflate(10, 10), border_radius=18)
        elif vehicle.id == hint_vehicle_id:
            pygame.draw.rect(surface, (168, 212, 233), vehicle_rect.inflate(8, 8), border_radius=18)

        pygame.draw.rect(surface, fill, vehicle_rect, border_radius=16)
        pygame.draw.rect(surface, border_color, vehicle_rect, width=2, border_radius=16)
        label = fonts["heading"].render(vehicle.id, True, WHITE)
        surface.blit(label, label.get_rect(center=vehicle_rect.center))

    return rects


def draw_stats_block(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    title: str,
    lines: list[str],
    rect: pygame.Rect,
) -> None:
    panel_card(surface, rect)
    draw_text(surface, fonts["heading"], title, TEXT, (rect.x + 18, rect.y + 16))
    for index, line in enumerate(lines):
        draw_text(surface, fonts["body"], line, TEXT, (rect.x + 18, rect.y + 58 + index * 32))


def format_seconds(seconds: float) -> str:
    minutes = int(seconds) // 60
    remainder = int(seconds) % 60
    return f"{minutes:02d}:{remainder:02d}"


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))
