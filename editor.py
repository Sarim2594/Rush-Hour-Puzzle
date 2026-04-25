from __future__ import annotations

from dataclasses import dataclass

import pygame

from board import Board, RED_VEHICLE_ID, Vehicle
from storage import CUSTOM_PUZZLES_DIR, load_board, save_custom_puzzle
from ui import (
    ACCENT,
    MUTED,
    PANEL_BG,
    TEXT,
    WHITE,
    Button,
    clamp,
    draw_background,
    draw_board,
    draw_panel_title,
    draw_screen_title,
    draw_text,
    get_board_screen_layout,
    layout_buttons_in_rect,
    make_button_row,
    measure_text_panel_height,
    panel_card,
    set_board_geometry,
    screen_to_cell,
)


@dataclass
class EditorMode:
    def _orientation_button_label(self) -> str:
        return f"Toggle ({self.pending_orientation})"

    def _sync_orientation_button(self) -> None:
        for button in self.buttons:
            if button.action == "toggle_orientation":
                button.label = self._orientation_button_label()
                break

    def __post_init__(self) -> None:
        self.vehicles: list[Vehicle] = [
            Vehicle(id=RED_VEHICLE_ID, row=2, col=0, length=2, orientation="H", is_red=True)
        ]
        self.pending_orientation = "H"
        self.pending_length = 2
        self.selected_vehicle_id: str | None = None
        self.puzzle_name = "custom_puzzle"
        self.message = "Click a grid cell to place or move vehicles."
        self.loadable_paths = self.refresh_saved_paths()
        self._saved_item_rects: list[pygame.Rect] = []
        self.buttons = (
            make_button_row(
                [("Back", "back"), ("Save", "save"), ("Delete", "delete"), ("Clear", "clear")],
                0,
                540,
                width=96,
                gap=8,
            )
            + make_button_row(
                [
                    ("Car", "car"),
                    ("Truck", "truck"),
                    (self._orientation_button_label(), "toggle_orientation"),
                ],
                0,
                540,
                width=96,
                gap=8,
            )
        )

    def refresh_saved_paths(self) -> list:
        CUSTOM_PUZZLES_DIR.mkdir(exist_ok=True)
        return sorted(CUSTOM_PUZZLES_DIR.glob("*.json"))

    def current_board(self) -> Board | None:
        try:
            return Board(self.vehicles, metadata={"id": self.puzzle_name, "name": self.puzzle_name.title()})
        except ValueError:
            return None

    def next_vehicle_id(self) -> str:
        used = {vehicle.id for vehicle in self.vehicles}
        for code in range(ord("A"), ord("Z") + 1):
            candidate = chr(code)
            if candidate not in used and candidate != RED_VEHICLE_ID:
                return candidate
        raise ValueError("No vehicle ids available.")

    def place_vehicle(self, row: int, col: int) -> None:
        if self.selected_vehicle_id:
            self.move_selected(row, col)
            return

        candidate = Vehicle(
            id=self.next_vehicle_id(),
            row=row,
            col=col,
            length=self.pending_length,
            orientation=self.pending_orientation,
            is_red=False,
        )
        candidate_list = self.vehicles + [candidate]

        try:
            Board(candidate_list, metadata={"id": self.puzzle_name, "name": self.puzzle_name.title()})
            self.vehicles = sorted(candidate_list, key=lambda vehicle: vehicle.id)
            self.message = "Vehicle placed."
        except ValueError as exc:
            self.message = str(exc)

    def move_selected(self, row: int, col: int) -> None:
        if not self.selected_vehicle_id:
            return
        updated: list[Vehicle] = []
        target = None
        for vehicle in self.vehicles:
            if vehicle.id == self.selected_vehicle_id:
                target = Vehicle(
                    id=vehicle.id,
                    row=row,
                    col=col,
                    length=vehicle.length,
                    orientation=vehicle.orientation,
                    is_red=vehicle.is_red,
                )
                updated.append(target)
            else:
                updated.append(vehicle)
        try:
            Board(updated, metadata={"id": self.puzzle_name, "name": self.puzzle_name.title()})
            self.vehicles = sorted(updated, key=lambda vehicle: vehicle.id)
            self.message = f"Moved {self.selected_vehicle_id}."
            self.selected_vehicle_id = None
        except ValueError as exc:
            self.message = str(exc)

    def delete_selected(self) -> None:
        if not self.selected_vehicle_id:
            self.message = "Select a vehicle to delete."
            return
        if self.selected_vehicle_id == RED_VEHICLE_ID:
            self.message = "The red car cannot be deleted."
            return
        self.vehicles = [vehicle for vehicle in self.vehicles if vehicle.id != self.selected_vehicle_id]
        self.message = f"Deleted {self.selected_vehicle_id}."
        self.selected_vehicle_id = None

    def save(self) -> None:
        board = self.current_board()
        if not board:
            self.message = "Board is invalid and cannot be saved."
            return
        save_custom_puzzle(board, self.puzzle_name)
        self.loadable_paths = self.refresh_saved_paths()
        self.message = f"Saved {self.puzzle_name}.json"

    def clear(self) -> None:
        self.vehicles = [Vehicle(id=RED_VEHICLE_ID, row=2, col=0, length=2, orientation="H", is_red=True)]
        self.selected_vehicle_id = None
        self.message = "Editor cleared."

    def load_file(self, index: int) -> None:
        if not (0 <= index < len(self.loadable_paths)):
            return
        board = load_board(self.loadable_paths[index])
        self.vehicles = list(board.vehicles)
        self.puzzle_name = board.metadata.get("id", self.loadable_paths[index].stem)
        self.selected_vehicle_id = None
        self.message = f"Loaded {self.puzzle_name}."

    def handle_event(self, event: pygame.event.Event) -> str | None:
        surface = pygame.display.get_surface()
        if surface is not None:
            set_board_geometry(get_board_screen_layout(surface, sidebar_min_width=360).board)
        for button in self.buttons:
            action = button.handle_event(event)
            if action:
                if action == "back":
                    return "back"
                if action == "save":
                    self.save()
                elif action == "delete":
                    self.delete_selected()
                elif action == "clear":
                    self.clear()
                elif action == "car":
                    self.pending_length = 2
                elif action == "truck":
                    self.pending_length = 3
                elif action == "toggle_orientation":
                    self.pending_orientation = "V" if self.pending_orientation == "H" else "H"
                self._sync_orientation_button()
                return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"
            if event.key == pygame.K_DELETE:
                self.delete_selected()
            elif event.key == pygame.K_s:
                self.save()
            elif event.key == pygame.K_c:
                self.clear()
            elif event.key == pygame.K_BACKSPACE:
                self.puzzle_name = self.puzzle_name[:-1] or "custom_puzzle"
            elif event.unicode and (event.unicode.isalnum() or event.unicode in {"_", "-"}):
                if self.puzzle_name == "custom_puzzle":
                    self.puzzle_name = event.unicode.lower()
                else:
                    self.puzzle_name += event.unicode.lower()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = screen_to_cell(event.pos)
            if cell:
                row, col = cell
                for vehicle in self.vehicles:
                    if (row, col) in vehicle.cells:
                        self.selected_vehicle_id = vehicle.id
                        self.message = f"Selected {vehicle.id}. Click an empty anchor cell to move it."
                        return None
                self.place_vehicle(row, col)
                return None

            for index, path in enumerate(self.loadable_paths[:6]):
                if index >= len(self._saved_item_rects):
                    break
                rect = self._saved_item_rects[index]
                if rect.collidepoint(event.pos):
                    self.load_file(index)
                    return None

        return None

    def update(self, dt: float) -> None:
        return None

    def _layout(self, surface: pygame.Surface) -> dict[str, pygame.Rect]:
        base = get_board_screen_layout(surface, sidebar_min_width=360)
        sidebar = base.sidebar
        gap = base.chrome.gap
        config_h = measure_text_panel_height(6, top_padding=58, line_gap=26, bottom_padding=18)
        buttons_h = 96
        buttons_gap = gap + 30
        config_rect = pygame.Rect(sidebar.x, sidebar.y, sidebar.width, config_h)
        buttons_rect = pygame.Rect(sidebar.x, sidebar.bottom - buttons_h, sidebar.width, buttons_h)
        saved_top = config_rect.bottom + gap
        saved_height = buttons_rect.y - buttons_gap - saved_top
        saved_h = min(380, max(0, saved_height))
        saved_rect = pygame.Rect(sidebar.x, saved_top, sidebar.width, saved_h)
        buttons_rect.y = sidebar.bottom - buttons_h
        return {
            "board": base.board,
            "config": config_rect,
            "saved": saved_rect,
            "buttons": buttons_rect,
        }

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        draw_background(surface)
        mouse_pos = pygame.mouse.get_pos()
        draw_screen_title(
            surface,
            fonts,
            "Puzzle Editor",
            "Build layouts, place vehicles, and save custom Rush Hour boards cleanly on any screen.",
        )
        layout = self._layout(surface)

        board = self.current_board()
        draw_board(
            surface,
            board or Board(self.vehicles, metadata={"id": "preview", "name": "Preview"}),
            fonts,
            selected_vehicle_id=self.selected_vehicle_id,
            board_area=layout["board"],
        )

        config_rect = layout["config"]
        panel_card(surface, config_rect)
        draw_panel_title(surface, fonts, config_rect, "Editor Settings")
        config_lines = [
            f"Name: {self.puzzle_name[:18]}",
            f"Selected: {self.selected_vehicle_id or '-'}",
            f"Add mode: {self.pending_length}-tile vehicle",
            f"Orientation: {self.pending_orientation}",
            "Type letters, numbers, _ or - to rename.",
            "Tip: click a vehicle, then click a new anchor cell.",
        ]
        for index, line in enumerate(config_lines):
            color = MUTED if index >= 4 else TEXT
            draw_text(surface, fonts["small"], line, color, (config_rect.x + 18, config_rect.y + 58 + index * 26))

        saved_rect = layout["saved"]
        panel_card(surface, saved_rect)
        draw_panel_title(surface, fonts, saved_rect, "Saved Custom Puzzles")
        self._saved_item_rects = []
        if not self.loadable_paths:
            draw_text(surface, fonts["small"], "No saved custom puzzles yet.", MUTED, (saved_rect.x + 18, saved_rect.y + 62))
        for index, path in enumerate(self.loadable_paths[:6]):
            rect = pygame.Rect(saved_rect.x + 12, saved_rect.y + 52 + index * 24, saved_rect.width - 24, 22)
            self._saved_item_rects.append(rect)
            hovered = rect.collidepoint(mouse_pos)
            fill = (230, 238, 248) if hovered else PANEL_BG
            pygame.draw.rect(surface, fill, rect, border_radius=6)
            pygame.draw.rect(surface, (205, 206, 198), rect, width=1, border_radius=6)
            draw_text(surface, fonts["small"], path.stem[:30], TEXT, (rect.x + 10, rect.y + 2))

        layout_buttons_in_rect(
            self.buttons,
            layout["buttons"],
            min_width=96,
            max_width=170,
            gap=10,
            fixed_height=42,
            max_columns=4,
        )

        for button in self.buttons:
            button.draw(surface, fonts, mouse_pos)
