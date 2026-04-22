from __future__ import annotations

from dataclasses import dataclass

import pygame

from board import Board, RED_VEHICLE_ID, Vehicle
from storage import CUSTOM_PUZZLES_DIR, load_board, save_custom_puzzle
from ui import (
    ACCENT,
    BACKGROUND,
    MUTED,
    PANEL_X,
    TEXT,
    WHITE,
    Button,
    draw_board,
    draw_text,
    make_button_row,
    panel_card,
    screen_to_cell,
)


@dataclass
class EditorMode:
    def __post_init__(self) -> None:
        self.vehicles: list[Vehicle] = [
            Vehicle(id=RED_VEHICLE_ID, row=2, col=0, length=2, orientation="H", is_red=True)
        ]
        self.pending_kind = "normal"
        self.pending_orientation = "H"
        self.pending_length = 2
        self.selected_vehicle_id: str | None = None
        self.puzzle_name = "custom_puzzle"
        self.message = "Click a grid cell to place or move vehicles."
        self.loadable_paths = self.refresh_saved_paths()
        self.buttons = (
            make_button_row(
                [("Back", "back"), ("Save", "save"), ("Delete", "delete"), ("Clear", "clear")],
                PANEL_X,
                520,
                width=98,
            )
            + make_button_row(
                [("Add Car", "car"), ("Add Truck", "truck"), ("Add Red", "red"), ("Toggle H/V", "toggle_orientation")],
                PANEL_X,
                582,
                width=98,
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

        if self.pending_kind == "red":
            replacement = Vehicle(id=RED_VEHICLE_ID, row=row, col=col, length=2, orientation="H", is_red=True)
            remaining = [vehicle for vehicle in self.vehicles if not vehicle.is_red]
            candidate_list = remaining + [replacement]
        else:
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
                    self.pending_kind = "normal"
                    self.pending_length = 2
                elif action == "truck":
                    self.pending_kind = "normal"
                    self.pending_length = 3
                elif action == "red":
                    self.pending_kind = "red"
                    self.pending_orientation = "H"
                    self.pending_length = 2
                elif action == "toggle_orientation":
                    self.pending_orientation = "V" if self.pending_orientation == "H" else "H"
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

            saved_list_origin = (PANEL_X, 140)
            for index, path in enumerate(self.loadable_paths[:6]):
                rect = pygame.Rect(saved_list_origin[0], saved_list_origin[1] + index * 54, 340, 42)
                if rect.collidepoint(event.pos):
                    self.load_file(index)
                    return None

        return None

    def update(self, dt: float) -> None:
        return None

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        surface.fill(BACKGROUND)
        mouse_pos = pygame.mouse.get_pos()
        draw_text(surface, fonts["title"], "Puzzle Editor", TEXT, (60, 28))

        board = self.current_board()
        draw_board(surface, board or Board(self.vehicles, metadata={"id": "preview", "name": "Preview"}), fonts, selected_vehicle_id=self.selected_vehicle_id)

        config_rect = pygame.Rect(PANEL_X, 90, 360, 220)
        panel_card(surface, config_rect)
        draw_text(surface, fonts["heading"], "Editor Settings", TEXT, (config_rect.x + 18, config_rect.y + 16))
        config_lines = [
            f"Name: {self.puzzle_name}",
            f"Selected: {self.selected_vehicle_id or '-'}",
            f"Add mode: {'Red car' if self.pending_kind == 'red' else f'{self.pending_length}-tile vehicle'}",
            f"Orientation: {self.pending_orientation}",
            "Type letters, numbers, _ or - to rename.",
            "Tip: click a vehicle, then click a new anchor cell.",
        ]
        for index, line in enumerate(config_lines):
            draw_text(surface, fonts["small"], line, MUTED if index >= 4 else TEXT, (config_rect.x + 18, config_rect.y + 58 + index * 26))

        saved_rect = pygame.Rect(PANEL_X, 326, 360, 176)
        panel_card(surface, saved_rect)
        draw_text(surface, fonts["heading"], "Saved Custom Puzzles", TEXT, (saved_rect.x + 18, saved_rect.y + 16))
        if not self.loadable_paths:
            draw_text(surface, fonts["small"], "No saved custom puzzles yet.", MUTED, (saved_rect.x + 18, saved_rect.y + 58))
        for index, path in enumerate(self.loadable_paths[:6]):
            rect = pygame.Rect(saved_rect.x + 12, saved_rect.y + 48 + index * 54, 336, 42)
            color = ACCENT if rect.collidepoint(mouse_pos) else WHITE
            pygame.draw.rect(surface, color, rect, border_radius=12)
            pygame.draw.rect(surface, TEXT, rect, width=2, border_radius=12)
            draw_text(surface, fonts["small"], path.stem, TEXT if color == WHITE else WHITE, (rect.x + 14, rect.y + 10))

        message_rect = pygame.Rect(PANEL_X, 640, 360, 72)
        panel_card(surface, message_rect)
        draw_text(surface, fonts["small"], self.message, TEXT, (message_rect.x + 18, message_rect.y + 24))

        for button in self.buttons:
            button.draw(surface, fonts, mouse_pos)
