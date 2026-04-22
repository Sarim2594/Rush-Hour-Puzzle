from __future__ import annotations

from dataclasses import dataclass

import pygame

from astar_solver import SolveResult, solve_astar
from board import Board
from ui import (
    BACKGROUND,
    MUTED,
    PANEL_X,
    TEXT,
    Button,
    draw_board,
    draw_stats_block,
    draw_text,
    format_seconds,
    make_button_row,
    panel_card,
)


StateKey = tuple[tuple[str, int, int], ...]


@dataclass
class DemoMode:
    initial_board: Board
    puzzle_name: str

    def __post_init__(self) -> None:
        self.display_board = self.initial_board
        self.result: SolveResult | None = None
        self.solution_states: list[StateKey] = [self.initial_board.state_key()]
        self.graph_sample_keys: list[StateKey] = []
        self.graph_positions: dict[StateKey, tuple[int, int]] = {}
        self.phase = "idle"
        self.sequence_index = 0
        self.timer = 0.0
        self.exploration_interval = 0.16
        self.solution_interval = 0.32
        self.message = "Press Start Demo to open the traversal view."
        self.buttons = make_button_row(
            [
                ("Back", "back"),
                ("Start Demo", "start"),
                ("Reset", "reset"),
                ("Slower", "slower"),
                ("Faster", "faster"),
            ],
            PANEL_X,
            520,
            width=96,
            gap=8,
        )

    def start_demo(self) -> None:
        self.result = solve_astar(self.initial_board, capture_exploration=True)
        self.display_board = self.initial_board
        self.sequence_index = 0
        self.timer = 0.0
        self.build_solution_states()
        self.build_graph_layout()
        if not self.result.solved:
            self.phase = "finished"
            self.message = "Solver did not find a solution."
            return
        self.phase = "exploration"
        self.message = "Showing graph traversal and expanded board states..."

    def reset(self) -> None:
        self.display_board = self.initial_board
        self.phase = "idle"
        self.sequence_index = 0
        self.timer = 0.0
        self.solution_states = [self.initial_board.state_key()]
        self.message = "Demo reset."

    def handle_event(self, event: pygame.event.Event) -> str | None:
        for button in self.buttons:
            action = button.handle_event(event)
            if action:
                if action == "back":
                    return "back"
                if action == "start":
                    self.start_demo()
                elif action == "reset":
                    self.reset()
                elif action == "slower":
                    self.exploration_interval = min(0.8, self.exploration_interval + 0.04)
                    self.solution_interval = min(1.0, self.solution_interval + 0.05)
                elif action == "faster":
                    self.exploration_interval = max(0.05, self.exploration_interval - 0.04)
                    self.solution_interval = max(0.08, self.solution_interval - 0.05)
                return None

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "back"
        return None

    def update(self, dt: float) -> None:
        if not self.result or self.phase == "idle" or self.phase == "finished":
            return

        self.timer += dt
        if self.phase == "exploration":
            if self.timer >= self.exploration_interval:
                self.timer = 0.0
                self.sequence_index += 1
                if self.sequence_index >= len(self.result.exploration_order):
                    self.phase = "solution"
                    self.display_board = self.initial_board
                    self.sequence_index = 0
                    self.message = "Traversal complete. Replaying the optimal path..."
                else:
                    self.display_board = self.result.exploration_order[self.sequence_index]
        elif self.phase == "solution":
            if self.timer >= self.solution_interval:
                self.timer = 0.0
                if self.sequence_index >= len(self.result.moves):
                    self.phase = "finished"
                    self.message = f"Optimal solution complete in {self.result.path_length} moves."
                else:
                    move = self.result.moves[self.sequence_index]
                    self.display_board = self.display_board.apply_move(move)
                    self.sequence_index += 1

    def build_solution_states(self) -> None:
        if not self.result:
            self.solution_states = [self.initial_board.state_key()]
            return
        board = self.initial_board
        states = [board.state_key()]
        for move in self.result.moves:
            board = board.apply_move(move)
            states.append(board.state_key())
        self.solution_states = states

    def build_graph_layout(self) -> None:
        if not self.result:
            self.graph_sample_keys = []
            self.graph_positions = {}
            return
        keys = [board.state_key() for board in self.result.exploration_order]
        if not keys:
            self.graph_sample_keys = []
            self.graph_positions = {}
            return

        max_nodes = 160
        if len(keys) <= max_nodes:
            sampled_indices = list(range(len(keys)))
        else:
            step = (len(keys) - 1) / (max_nodes - 1)
            sampled_indices = sorted({int(round(index * step)) for index in range(max_nodes)})

        sampled_keys = [keys[index] for index in sampled_indices]
        unique_depths = sorted({self.result.depth_by_key.get(key, 0) for key in sampled_keys})
        depth_columns = {depth: index for index, depth in enumerate(unique_depths)}
        graph_rect = pygame.Rect(PANEL_X, 90, 490, 360)
        levels: dict[int, list[StateKey]] = {}
        for key in sampled_keys:
            levels.setdefault(self.result.depth_by_key.get(key, 0), []).append(key)

        positions: dict[StateKey, tuple[int, int]] = {}
        column_count = max(1, len(unique_depths))
        for depth, level_keys in levels.items():
            column = depth_columns[depth]
            x = graph_rect.x + 30 + int(column * (graph_rect.width - 60) / max(1, column_count - 1))
            for index, key in enumerate(level_keys):
                y = graph_rect.y + 36 + int((index + 1) * (graph_rect.height - 72) / (len(level_keys) + 1))
                positions[key] = (x, y)

        self.graph_sample_keys = sampled_keys
        self.graph_positions = positions

    def current_graph_key(self) -> StateKey:
        if self.phase == "exploration" and self.result and self.result.exploration_order:
            index = min(self.sequence_index, len(self.result.exploration_order) - 1)
            return self.result.exploration_order[index].state_key()
        if self.phase == "solution" and self.solution_states:
            index = min(self.sequence_index, len(self.solution_states) - 1)
            return self.solution_states[index]
        return self.display_board.state_key()

    def draw_graph_panel(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        graph_rect = pygame.Rect(PANEL_X, 90, 490, 360)
        panel_card(surface, graph_rect)
        draw_text(surface, fonts["heading"], "Search Graph", TEXT, (graph_rect.x + 18, graph_rect.y + 16))
        if not self.result or not self.graph_sample_keys:
            draw_text(surface, fonts["small"], "Start the demo to visualize A* traversal.", MUTED, (graph_rect.x + 18, graph_rect.y + 58))
            return

        current_key = self.current_graph_key()
        solution_set = set(self.solution_states)
        for key in self.graph_sample_keys:
            parent_key = self.result.parent_by_key.get(key)
            if parent_key and parent_key in self.graph_positions:
                pygame.draw.line(surface, (176, 171, 160), self.graph_positions[parent_key], self.graph_positions[key], 1)

        for key in self.graph_sample_keys:
            pos = self.graph_positions[key]
            radius = 7
            color = (137, 145, 156)
            if key in solution_set:
                color = (86, 150, 109)
                radius = 8
            if key == current_key:
                color = (198, 102, 71)
                radius = 10
            pygame.draw.circle(surface, color, pos, radius)

        draw_text(surface, fonts["small"], "Sampled expanded states arranged by search depth.", MUTED, (graph_rect.x + 18, graph_rect.bottom - 30))

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        surface.fill(BACKGROUND)
        mouse_pos = pygame.mouse.get_pos()
        draw_text(surface, fonts["title"], f"Visual Demo: {self.puzzle_name}", TEXT, (60, 28))
        draw_board(surface, self.display_board, fonts)
        self.draw_graph_panel(surface, fonts)

        lines = [
            f"Phase: {self.phase.title()}",
            f"Explored: {self.result.explored_states if self.result else 0}",
            f"Frontier peak: {self.result.frontier_peak if self.result else 0}",
            f"Solution length: {self.result.path_length if self.result else 0}",
            f"Elapsed solve time: {format_seconds(self.result.elapsed_time if self.result else 0.0)}",
        ]
        draw_stats_block(surface, fonts, "Demo Stats", lines, pygame.Rect(PANEL_X, 468, 348, 172))

        info_rect = pygame.Rect(PANEL_X + 362, 468, 128, 172)
        panel_card(surface, info_rect)
        draw_text(surface, fonts["heading"], "View", TEXT, (info_rect.x + 18, info_rect.y + 16))
        info_lines = [
            "Board",
            "and",
            "graph",
            "side by side",
        ]
        for index, line in enumerate(info_lines):
            draw_text(surface, fonts["small"], line, MUTED, (info_rect.x + 18, info_rect.y + 58 + index * 24))

        message_rect = pygame.Rect(PANEL_X, 650, 490, 62)
        panel_card(surface, message_rect)
        draw_text(surface, fonts["small"], self.message, TEXT, (message_rect.x + 18, message_rect.y + 20))

        for button in self.buttons:
            button.draw(surface, fonts, mouse_pos)
