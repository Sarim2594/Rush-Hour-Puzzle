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

BACKGROUND = (236, 232, 222)
PANEL_BG = (252, 250, 244)
PANEL_EDGE = (199, 192, 180)
TEXT = (58, 56, 52)
MUTED = (122, 116, 106)
ACCENT = (58, 128, 210)
ACCENT_DARK = (40, 93, 156)
SUCCESS = (67, 148, 94)
WARNING = (211, 163, 74)
HINT = (76, 150, 226)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

ROAD_DARK = (63, 66, 72)
ROAD_LIGHT = (76, 79, 86)
STALL_LINE = (220, 220, 214)
EXIT_YELLOW = (236, 198, 72)
RED_CAR = (210, 52, 52)
VEHICLE_PALETTE = [
    (78, 111, 153),
    (84, 132, 97),
    (179, 141, 67),
    (94, 124, 136),
    (123, 101, 142),
    (138, 114, 88),
    (83, 126, 147),
]


def create_fonts() -> dict[str, pygame.font.Font]:
    return {
        "title": pygame.font.SysFont("segoeui", 34, bold=True),
        "heading": pygame.font.SysFont("segoeui", 24, bold=True),
        "body": pygame.font.SysFont("segoeui", 19),
        "small": pygame.font.SysFont("segoeui", 16),
        "button": pygame.font.SysFont("segoeui", 20, bold=True),
        "tiny": pygame.font.SysFont("segoeui", 13),
    }


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
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


def _clamp_color(color: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c))) for c in color)  # type: ignore[return-value]


def _shade(color: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    return _clamp_color((color[0] + amount, color[1] + amount, color[2] + amount))


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    position: tuple[int, int],
) -> None:
    rendered = font.render(text, True, color)
    surface.blit(rendered, position)


def ellipsize_text(font: pygame.font.Font, text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    suffix = "..."
    suffix_width = font.size(suffix)[0]
    if suffix_width > max_width:
        return ""
    trimmed = text
    while trimmed and font.size(trimmed)[0] + suffix_width > max_width:
        trimmed = trimmed[:-1]
    return f"{trimmed}{suffix}" if trimmed else suffix


def panel_card(surface: pygame.Surface, rect: pygame.Rect) -> None:
    shadow_rect = rect.move(0, 3)
    shadow = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
    shadow.fill((0, 0, 0, 42))
    surface.blit(shadow, shadow_rect.topleft)
    pygame.draw.rect(surface, PANEL_BG, rect, border_radius=10)
    pygame.draw.rect(surface, PANEL_EDGE, rect, width=1, border_radius=10)


def draw_background(surface: pygame.Surface) -> None:
    width, height = surface.get_size()
    surface.fill(BACKGROUND)
    pygame.draw.rect(surface, (218, 212, 200), pygame.Rect(0, height - 120, width, 120))


def draw_scanlines(surface: pygame.Surface, alpha: int = 28) -> None:
    return None


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Button:
    label: str
    rect: pygame.Rect
    action: str
    fill: tuple[int, int, int] = ACCENT
    text_color: tuple[int, int, int] = WHITE

    def _fit_label(self, fonts: dict[str, pygame.font.Font], max_width: int) -> pygame.Surface:
        candidates = [fonts["button"], fonts["small"], fonts["tiny"]]
        for font in candidates:
            rendered = font.render(self.label, True, self.text_color)
            if rendered.get_width() <= max_width:
                return rendered
        tiny = fonts["tiny"]
        text = self.label
        while text:
            shortened = f"{text}..."
            rendered = tiny.render(shortened, True, self.text_color)
            if rendered.get_width() <= max_width:
                return rendered
            text = text[:-1]
        return tiny.render("...", True, self.text_color)

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font], mouse_pos: tuple[int, int]) -> None:
        hovered = self.rect.collidepoint(mouse_pos)
        shadow = self.rect.move(0, 2)
        shadow_surf = pygame.Surface(shadow.size, pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 52))
        surface.blit(shadow_surf, shadow.topleft)
        fill = _shade(self.fill, -12) if hovered else self.fill
        pygame.draw.rect(surface, fill, self.rect, border_radius=8)
        pygame.draw.rect(surface, _shade(fill, -36), self.rect, width=1, border_radius=8)
        rendered = self._fit_label(fonts, self.rect.width - 12)
        center = self.rect.center
        surface.blit(rendered, rendered.get_rect(center=center))

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            return self.action
        return None


def make_button_row(
    labels: list[tuple[str, str]],
    x: int,
    y: int,
    width: int = 150,
    gap: int = 12,
    height: int = 48,
) -> list[Button]:
    buttons: list[Button] = []
    for index, (label, action) in enumerate(labels):
        rect = pygame.Rect(x + index * (width + gap), y, width, height)
        buttons.append(Button(label=label, rect=rect, action=action, fill=ACCENT))
    return buttons


# ---------------------------------------------------------------------------
# Board drawing
# ---------------------------------------------------------------------------
def _draw_dashed_rect(surface: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int], dash: int = 12, gap: int = 7) -> None:
    for x in range(rect.left, rect.right, dash + gap):
        pygame.draw.line(surface, color, (x, rect.top), (min(x + dash, rect.right), rect.top), 2)
        pygame.draw.line(surface, color, (x, rect.bottom), (min(x + dash, rect.right), rect.bottom), 2)
    for y in range(rect.top, rect.bottom, dash + gap):
        pygame.draw.line(surface, color, (rect.left, y), (rect.left, min(y + dash, rect.bottom)), 2)
        pygame.draw.line(surface, color, (rect.right, y), (rect.right, min(y + dash, rect.bottom)), 2)


def _draw_wheels(surface: pygame.Surface, body: pygame.Rect, orientation: str, length: int) -> None:
    tire = (28, 28, 30)
    rim = (132, 136, 143)
    if orientation == "H":
        step = body.width // max(2, length)
        for i in range(length):
            wx = body.left + i * step + step // 2 - 8
            top_wheel = pygame.Rect(wx, body.top - 5, 16, 7)
            bot_wheel = pygame.Rect(wx, body.bottom - 2, 16, 7)
            pygame.draw.rect(surface, tire, top_wheel, border_radius=3)
            pygame.draw.rect(surface, tire, bot_wheel, border_radius=3)
            pygame.draw.rect(surface, rim, top_wheel.inflate(-8, -3), border_radius=2)
            pygame.draw.rect(surface, rim, bot_wheel.inflate(-8, -3), border_radius=2)
    else:
        step = body.height // max(2, length)
        for i in range(length):
            wy = body.top + i * step + step // 2 - 8
            left_wheel = pygame.Rect(body.left - 5, wy, 7, 16)
            right_wheel = pygame.Rect(body.right - 2, wy, 7, 16)
            pygame.draw.rect(surface, tire, left_wheel, border_radius=3)
            pygame.draw.rect(surface, tire, right_wheel, border_radius=3)
            pygame.draw.rect(surface, rim, left_wheel.inflate(-3, -8), border_radius=2)
            pygame.draw.rect(surface, rim, right_wheel.inflate(-3, -8), border_radius=2)


def draw_vehicle(surface: pygame.Surface, rect: pygame.Rect, *, orientation: str, length: int, is_red: bool, color: tuple[int, int, int]) -> None:
    shadow = rect.move(2, 2)
    pygame.draw.rect(surface, (0, 0, 0, 35), shadow, border_radius=10)
    body = rect.inflate(-6, -6)
    pygame.draw.rect(surface, _shade(color, -22), body, border_radius=12)
    shell = body.inflate(-2, -2)
    pygame.draw.rect(surface, color, shell, border_radius=12)
    pygame.draw.rect(surface, _shade(color, 20), shell.inflate(-6, -6), width=2, border_radius=10)
    pygame.draw.rect(surface, _shade(color, -40), shell, width=2, border_radius=12)

    glass = (173, 204, 220)
    if length == 2:
        if orientation == "H":
            hood = pygame.Rect(shell.left + 6, shell.top + 6, int(shell.width * 0.25), shell.height - 12)
            cabin = pygame.Rect(hood.right + 4, shell.top + 8, int(shell.width * 0.42), shell.height - 16)
            trunk = pygame.Rect(cabin.right + 4, shell.top + 6, shell.right - cabin.right - 10, shell.height - 12)
            windshield = pygame.Rect(cabin.left + 2, cabin.top + 2, cabin.width // 2 - 3, cabin.height - 4)
            rear_glass = pygame.Rect(cabin.centerx + 1, cabin.top + 2, cabin.width // 2 - 3, cabin.height - 4)
            headlight = pygame.Rect(shell.right - 9, shell.top + 11, 4, shell.height - 22)
            taillight = pygame.Rect(shell.left + 5, shell.top + 11, 4, shell.height - 22)
            pygame.draw.rect(surface, _shade(color, -5), hood, border_radius=8)
            pygame.draw.rect(surface, _shade(color, 10), trunk, border_radius=8)
            arch_top = pygame.Rect(shell.left + 12, shell.top - 1, shell.width - 24, 4)
            arch_bottom = pygame.Rect(shell.left + 12, shell.bottom - 3, shell.width - 24, 4)
            pygame.draw.rect(surface, _shade(color, -35), arch_top, border_radius=2)
            pygame.draw.rect(surface, _shade(color, -35), arch_bottom, border_radius=2)
        else:
            hood = pygame.Rect(shell.left + 6, shell.top + 6, shell.width - 12, int(shell.height * 0.25))
            cabin = pygame.Rect(shell.left + 8, hood.bottom + 4, shell.width - 16, int(shell.height * 0.42))
            trunk = pygame.Rect(shell.left + 6, cabin.bottom + 4, shell.width - 12, shell.bottom - cabin.bottom - 10)
            windshield = pygame.Rect(cabin.left + 2, cabin.top + 2, cabin.width - 4, cabin.height // 2 - 3)
            rear_glass = pygame.Rect(cabin.left + 2, cabin.centery + 1, cabin.width - 4, cabin.height // 2 - 3)
            headlight = pygame.Rect(shell.left + 11, shell.bottom - 9, shell.width - 22, 4)
            taillight = pygame.Rect(shell.left + 11, shell.top + 5, shell.width - 22, 4)
            pygame.draw.rect(surface, _shade(color, -5), hood, border_radius=8)
            pygame.draw.rect(surface, _shade(color, 10), trunk, border_radius=8)
            arch_left = pygame.Rect(shell.left - 1, shell.top + 12, 4, shell.height - 24)
            arch_right = pygame.Rect(shell.right - 3, shell.top + 12, 4, shell.height - 24)
            pygame.draw.rect(surface, _shade(color, -35), arch_left, border_radius=2)
            pygame.draw.rect(surface, _shade(color, -35), arch_right, border_radius=2)
        pygame.draw.rect(surface, _shade(color, -3), cabin, border_radius=8)
        pygame.draw.rect(surface, glass, windshield, border_radius=4)
        pygame.draw.rect(surface, glass, rear_glass, border_radius=4)
        pygame.draw.rect(surface, (252, 238, 184), headlight, border_radius=2)
        pygame.draw.rect(surface, (176, 52, 52), taillight, border_radius=2)
        if is_red:
            stripe = (
                pygame.Rect(shell.centerx - 3, shell.top + 8, 6, shell.height - 16)
                if orientation == "H"
                else pygame.Rect(shell.left + 8, shell.centery - 3, shell.width - 16, 6)
            )
            pygame.draw.rect(surface, (248, 248, 248), stripe, border_radius=3)
    else:
        if orientation == "H":
            cab = pygame.Rect(shell.left + 6, shell.top + 7, int(shell.width * 0.34), shell.height - 14)
            cargo = pygame.Rect(cab.right + 4, shell.top + 7, shell.right - cab.right - 10, shell.height - 14)
            front_light = pygame.Rect(cab.left + 3, cab.top + 8, 4, cab.height - 16)
            side_line1 = pygame.Rect(cargo.left + 6, cargo.top + 8, cargo.width - 12, 2)
            side_line2 = pygame.Rect(cargo.left + 6, cargo.bottom - 10, cargo.width - 12, 2)
        else:
            cab = pygame.Rect(shell.left + 7, shell.top + 6, shell.width - 14, int(shell.height * 0.34))
            cargo = pygame.Rect(shell.left + 7, cab.bottom + 4, shell.width - 14, shell.bottom - cab.bottom - 10)
            front_light = pygame.Rect(cab.left + 8, cab.top + 3, cab.width - 16, 4)
            side_line1 = pygame.Rect(cargo.left + 8, cargo.top + 6, 2, cargo.height - 12)
            side_line2 = pygame.Rect(cargo.right - 10, cargo.top + 6, 2, cargo.height - 12)
        pygame.draw.rect(surface, _shade(color, 18), cab, border_radius=5)
        pygame.draw.rect(surface, glass, cab.inflate(-8, -8), border_radius=4)
        pygame.draw.rect(surface, _shade(color, -8), cargo, border_radius=5)
        pygame.draw.rect(surface, (252, 238, 184), front_light, border_radius=2)
        pygame.draw.rect(surface, _shade(color, -26), side_line1, border_radius=2)
        pygame.draw.rect(surface, _shade(color, -26), side_line2, border_radius=2)
        for i in range(1, 3):
            if orientation == "H":
                y = cargo.top + i * (cargo.height // 3)
                pygame.draw.line(surface, _shade(color, -24), (cargo.left + 6, y), (cargo.right - 6, y), 2)
            else:
                x = cargo.left + i * (cargo.width // 3)
                pygame.draw.line(surface, _shade(color, -24), (x, cargo.top + 6), (x, cargo.bottom - 6), 2)
    _draw_wheels(surface, body, orientation, length)


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

    pygame.draw.rect(surface, ROAD_DARK, grid_rect, border_radius=10)
    pygame.draw.rect(surface, ROAD_LIGHT, grid_rect, width=2, border_radius=10)

    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            cell = cell_rect(row, col)
            _draw_dashed_rect(surface, cell.inflate(-8, -8), STALL_LINE)

    exit_cell = cell_rect(board.red_vehicle.row, GRID_SIZE - 1)
    exit_marker = pygame.Rect(exit_cell.right - 12, exit_cell.top + 6, 18, exit_cell.height - 12)
    stripe_h = max(6, exit_marker.height // 5)
    for idx in range(0, exit_marker.height, stripe_h):
        color = EXIT_YELLOW if (idx // stripe_h) % 2 == 0 else (42, 42, 42)
        pygame.draw.rect(surface, color, pygame.Rect(exit_marker.x, exit_marker.y + idx, exit_marker.width, stripe_h))
    pygame.draw.rect(surface, (32, 32, 32), exit_marker, width=1)
    arrow = fonts["heading"].render(">", True, EXIT_YELLOW)
    surface.blit(arrow, arrow.get_rect(midleft=(exit_marker.right + 6, exit_marker.centery)))

    hint_vehicle_id = hint_move.vehicle_id if hint_move else None
    for vehicle in board.vehicles:
        start_cell = cell_rect(vehicle.row, vehicle.col)
        width = vehicle.length * CELL_SIZE if vehicle.orientation == "H" else CELL_SIZE
        height = CELL_SIZE if vehicle.orientation == "H" else vehicle.length * CELL_SIZE
        v_rect = pygame.Rect(start_cell.x + 6, start_cell.y + 6, width - 12, height - 12)
        rects[vehicle.id] = v_rect

        fill = vehicle_color(vehicle.id, vehicle.is_red)

        outline_color = None
        if vehicle.id == selected_vehicle_id:
            outline_color = HINT
        elif vehicle.id == hint_vehicle_id:
            outline_color = WARNING
        if outline_color is not None:
            pygame.draw.rect(surface, outline_color, v_rect.inflate(8, 8), width=3, border_radius=12)

        draw_vehicle(
            surface,
            v_rect,
            orientation=vehicle.orientation,
            length=vehicle.length,
            is_red=vehicle.is_red,
            color=fill,
        )
        label = fonts["small"].render(vehicle.id, True, WHITE)
        surface.blit(label, label.get_rect(center=v_rect.center))

    return rects


def draw_stats_block(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    title: str,
    lines: list[str],
    rect: pygame.Rect,
) -> None:
    panel_card(surface, rect)
    draw_text(surface, fonts["heading"], title, TEXT, (rect.x + 18, rect.y + 14))
    underline = pygame.Rect(rect.x + 18, rect.y + 44, rect.width - 36, 1)
    pygame.draw.rect(surface, ACCENT, underline)
    for index, line in enumerate(lines):
        draw_text(surface, fonts["body"], line, TEXT, (rect.x + 18, rect.y + 56 + index * 28))


def format_seconds(seconds: float) -> str:
    minutes = int(seconds) // 60
    remainder = int(seconds) % 60
    return f"{minutes:02d}:{remainder:02d}"


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))
