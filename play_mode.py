from __future__ import annotations

from dataclasses import dataclass
import time

import pygame

from astar_solver import get_hint, solve_astar
from board import Board, Move
from storage import record_solve
from ui import (
    ACCENT,
    ACCENT_DARK,
    MUTED,
    PANEL_X,
    TEXT,
    CELL_SIZE,
    draw_background,
    draw_board,
    draw_stats_block,
    draw_text,
    format_seconds,
    make_button_row,
    panel_card,
    screen_to_cell,
)


@dataclass
class PlayMode:
    initial_board: Board
    puzzle_id: str
    puzzle_name: str

    def __post_init__(self) -> None:
        self.board = self.initial_board
        self.selected_vehicle_id: str | None = None
        self.message = "Drag a vehicle along its lane toward the exit."
        self.move_count = 0
        self.started_at = time.perf_counter()
        self.finished_at: float | None = None
        self.finished = False
        self.auto_solution: list[Move] = []
        self.auto_timer = 0.0
        self.auto_interval = 0.28
        self.drag_vehicle_id: str | None = None
        self.drag_origin_pos: tuple[int, int] | None = None
        self.drag_preview_distance = 0
        self.buttons = make_button_row(
            [("Back", "back"), ("Hint", "hint"), ("Solve", "solve"), ("Reset", "reset")],
            PANEL_X,
            500,
            width=108,
            gap=10,
        )

    def elapsed(self) -> float:
        end_time = self.finished_at if self.finished_at is not None else time.perf_counter()
        return max(0.0, end_time - self.started_at)

    def reset(self) -> None:
        self.board = self.initial_board
        self.selected_vehicle_id = None
        self.message = "Board reset."
        self.move_count = 0
        self.started_at = time.perf_counter()
        self.finished_at = None
        self.finished = False
        self.auto_solution = []
        self.auto_timer = 0.0
        self.drag_vehicle_id = None
        self.drag_origin_pos = None
        self.drag_preview_distance = 0

    def apply_single_hint(self) -> None:
        move = get_hint(self.board)
        if not move:
            self.message = "No hint available."
            return
        self.selected_vehicle_id = move.vehicle_id
        self.apply_player_move(move)
        if not self.finished:
            self.message = f"Hint played: moved {move.vehicle_id} by {move.distance:+d}."

    def apply_player_move(self, move: Move) -> None:
        self.board = self.board.apply_move(move)
        self.move_count += 1
        self.selected_vehicle_id = move.vehicle_id
        self.message = f"Moved {move.vehicle_id} by {move.distance:+d}."
        if self.board.is_goal() and not self.finished:
            self.finished = True
            self.finished_at = time.perf_counter()
            elapsed = self.elapsed()
            record_solve(self.puzzle_id, True, self.move_count, elapsed)
            self.message = f"Puzzle solved in {self.move_count} moves."

    def start_auto_solution(self) -> None:
        result = solve_astar(self.board)
        if not result.solved or not result.moves:
            self.message = "No solution found from this position."
            return
        self.auto_solution = list(result.moves)
        self.auto_timer = 0.0
        self.message = f"Auto-solving in {len(self.auto_solution)} optimal moves."

    def handle_event(self, event: pygame.event.Event) -> str | None:
        for button in self.buttons:
            action = button.handle_event(event)
            if action:
                if action == "back":
                    return "back"
                if action == "hint":
                    self.apply_single_hint()
                elif action == "solve":
                    self.start_auto_solution()
                elif action == "reset":
                    self.reset()
                return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"
            elif event.key == pygame.K_h:
                self.apply_single_hint()
            elif event.key == pygame.K_r:
                self.reset()
            elif event.key == pygame.K_s:
                self.start_auto_solution()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = screen_to_cell(event.pos)
            if cell:
                row, col = cell
                for vehicle in self.board.vehicles:
                    if (row, col) in vehicle.cells:
                        self.selected_vehicle_id = vehicle.id
                        self.drag_vehicle_id = vehicle.id
                        self.drag_origin_pos = event.pos
                        self.drag_preview_distance = 0
                        self.message = f"Dragging vehicle {vehicle.id}."
                        return None
                self.selected_vehicle_id = None

        if event.type == pygame.MOUSEMOTION and self.drag_vehicle_id and self.drag_origin_pos:
            vehicle = self.board.get_vehicle(self.drag_vehicle_id)
            dx = event.pos[0] - self.drag_origin_pos[0]
            dy = event.pos[1] - self.drag_origin_pos[1]
            delta = dx if vehicle.orientation == "H" else dy
            raw_steps = int(round(delta / CELL_SIZE))
            self.drag_preview_distance = self.resolve_drag_distance(vehicle.id, raw_steps)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag_vehicle_id:
            vehicle = self.board.get_vehicle(self.drag_vehicle_id)
            final_distance = self.drag_preview_distance
            self.drag_vehicle_id = None
            self.drag_origin_pos = None
            self.drag_preview_distance = 0
            if final_distance == 0:
                self.message = f"Selected vehicle {vehicle.id}."
                return None
            self.apply_player_move(Move(vehicle.id, final_distance))

        return None

    def update(self, dt: float) -> None:
        if self.auto_solution and not self.finished:
            self.auto_timer += dt
            if self.auto_timer >= self.auto_interval:
                self.auto_timer = 0.0
                move = self.auto_solution.pop(0)
                self.apply_player_move(move)

    def resolve_drag_distance(self, vehicle_id: str, requested_distance: int) -> int:
        if requested_distance == 0:
            return 0
        candidate = requested_distance
        while candidate != 0:
            if self.board.can_apply_move(Move(vehicle_id, candidate)):
                return candidate
            candidate += -1 if candidate > 0 else 1
        return 0

    def display_board(self) -> Board:
        if self.drag_vehicle_id and self.drag_preview_distance:
            return self.board.apply_move(Move(self.drag_vehicle_id, self.drag_preview_distance))
        return self.board

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        draw_background(surface)
        mouse_pos = pygame.mouse.get_pos()
        draw_text(surface, fonts["title"], self.puzzle_name, TEXT, (60, 28))
        draw_board(surface, self.display_board(), fonts, selected_vehicle_id=self.selected_vehicle_id)

        info_rect = pygame.Rect(PANEL_X, 100, 360, 176)
        draw_stats_block(
            surface,
            fonts,
            "Play Stats",
            [
                f"Moves: {self.move_count}",
                f"Time: {format_seconds(self.elapsed())}",
                f"Selected: {self.selected_vehicle_id or '-'}",
                f"Status: {'Solved' if self.finished else 'In progress'}",
            ],
            info_rect,
        )
        if self.finished:
            draw_text(surface, fonts["small"], "Solved!", ACCENT_DARK, (info_rect.x + 18, info_rect.bottom - 32))

        help_rect = pygame.Rect(PANEL_X, 300, 360, 184)
        panel_card(surface, help_rect)
        draw_text(surface, fonts["heading"], "Controls", TEXT, (help_rect.x + 18, help_rect.y + 14))
        pygame.draw.rect(surface, ACCENT, pygame.Rect(help_rect.x + 18, help_rect.y + 44, help_rect.width - 36, 1))
        help_lines = [
            "Drag a vehicle along its lane to move it.",
            "Hint plays exactly one optimal move.",
            "Solve replays the best solution.",
            "The board previews each tile while dragging.",
        ]
        for index, line in enumerate(help_lines):
            draw_text(surface, fonts["small"], line, MUTED, (help_rect.x + 18, help_rect.y + 56 + index * 28))

        message_rect = pygame.Rect(PANEL_X, 600, 360, 64)
        panel_card(surface, message_rect)
        draw_text(surface, fonts["small"], self.message[:46], TEXT, (message_rect.x + 18, message_rect.y + 22))

        for button in self.buttons:
            button.draw(surface, fonts, mouse_pos)
