from __future__ import annotations

from dataclasses import dataclass

import pygame

from astar_solver import SolveResult, solve_astar
from board import Board
from ui import (
    ACCENT,
    ACCENT_DARK,
    MUTED,
    SUCCESS,
    TEXT,
    WARNING,
    Button,
    draw_background,
    draw_board,
    draw_panel_title,
    draw_screen_title,
    draw_stats_block,
    draw_text,
    ellipsize_text,
    format_seconds,
    get_board_screen_layout,
    layout_buttons_in_rect,
    make_button_row,
    measure_stats_block_height,
    measure_text_panel_height,
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
            0,
            520,
            width=96,
            gap=8,
        )
        self._last_graph_rect: pygame.Rect | None = None

    def _layout(self, surface: pygame.Surface) -> dict[str, pygame.Rect]:
        base = get_board_screen_layout(surface, sidebar_min_width=360)
        sidebar = base.sidebar
        gap = base.chrome.gap
        message_h = 66
        buttons_h = 56 if sidebar.width >= 520 else 122
        stats_h = measure_stats_block_height(5)
        legend_h = measure_text_panel_height(3, top_padding=60, line_gap=26, bottom_padding=20)
        info_h = max(stats_h, legend_h)
        min_graph_h = 170 if not base.stacked else 150
        graph_h = max(min_graph_h, sidebar.height - info_h - buttons_h - message_h - gap * 3)
        graph_h = min(graph_h, max(min_graph_h, int(sidebar.height * 0.52)))
        graph_rect = pygame.Rect(sidebar.x, sidebar.y, sidebar.width, graph_h)
        row_top = graph_rect.bottom + gap
        stats_w = int(sidebar.width * (0.68 if sidebar.width > 430 else 0.62))
        legend_w = max(120, sidebar.width - stats_w - gap)
        stats_rect = pygame.Rect(sidebar.x, row_top, stats_w, info_h)
        legend_rect = pygame.Rect(stats_rect.right + gap, row_top, legend_w, info_h)
        buttons_y = row_top + info_h + gap
        message_y = buttons_y + buttons_h + gap
        if message_y + message_h > sidebar.bottom:
            overflow = message_y + message_h - sidebar.bottom
            graph_rect.height = max(min_graph_h, graph_rect.height - overflow)
            row_top = graph_rect.bottom + gap
            stats_rect.y = row_top
            legend_rect.y = row_top
            buttons_y = row_top + info_h + gap
            message_y = buttons_y + buttons_h + gap
        message_rect = pygame.Rect(sidebar.x, message_y, sidebar.width, message_h)
        buttons_rect = pygame.Rect(sidebar.x, buttons_y, sidebar.width, buttons_h)
        return {
            "board": base.board,
            "graph": graph_rect,
            "stats": stats_rect,
            "legend": legend_rect,
            "message": message_rect,
            "buttons": buttons_rect,
        }

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

    def build_graph_layout(self, graph_rect: pygame.Rect | None = None) -> None:
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
        if graph_rect is None:
            graph_rect = pygame.Rect(0, 0, 490, 370)
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

    def draw_graph_panel(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font], graph_rect: pygame.Rect) -> None:
        panel_card(surface, graph_rect)
        draw_text(surface, fonts["heading"], "Search Graph", TEXT, (graph_rect.x + 18, graph_rect.y + 14))
        pygame.draw.rect(surface, ACCENT, pygame.Rect(graph_rect.x + 18, graph_rect.y + 44, graph_rect.width - 36, 1))
        if not self.result or not self.graph_sample_keys:
            draw_text(surface, fonts["small"], "Press START to visualize A* traversal.", MUTED, (graph_rect.x + 18, graph_rect.y + 64))
            return

        current_key = self.current_graph_key()
        solution_set = set(self.solution_states)
        for key in self.graph_sample_keys:
            parent_key = self.result.parent_by_key.get(key)
            if parent_key and parent_key in self.graph_positions:
                pygame.draw.line(
                    surface,
                    (172, 170, 160),
                    self.graph_positions[parent_key],
                    self.graph_positions[key],
                    1,
                )

        for key in self.graph_sample_keys:
            pos = self.graph_positions[key]
            radius = 6
            color = (145, 146, 152)
            if key in solution_set:
                color = SUCCESS
                radius = 7
            if key == current_key:
                color = ACCENT
                radius = 10
            pygame.draw.circle(surface, color, pos, radius)

        draw_text(surface, fonts["small"], "Nodes arranged by search depth.", MUTED, (graph_rect.x + 18, graph_rect.bottom - 28))

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        draw_background(surface)
        mouse_pos = pygame.mouse.get_pos()
        layout = self._layout(surface)
        board_rect = layout["board"]
        graph_rect = layout["graph"]
        stats_rect = layout["stats"]
        legend_rect = layout["legend"]
        message_rect = layout["message"]
        buttons_rect = layout["buttons"]
        layout_buttons_in_rect(self.buttons, buttons_rect, min_width=90, max_width=130, gap=8)

        if self.result and (self._last_graph_rect is None or self._last_graph_rect.size != graph_rect.size):
            self.build_graph_layout(graph_rect)
            self._last_graph_rect = graph_rect.copy()

        draw_screen_title(
            surface,
            fonts,
            f"Visual Demo: {self.puzzle_name}",
            "Watch A* exploration, the graph frontier, and the final optimal replay.",
        )
        draw_board(surface, self.display_board, fonts, board_area=board_rect)
        self.draw_graph_panel(surface, fonts, graph_rect)

        solve_elapsed = self.result.elapsed_time if self.result else 0.0
        solve_time_text = f"{solve_elapsed:.3f}s" if solve_elapsed < 60 else format_seconds(solve_elapsed)
        lines = [
            f"Phase: {self.phase.title()}",
            f"A* solve time: {solve_time_text}",
            f"Explored: {self.result.explored_states if self.result else 0}",
            f"Frontier peak: {self.result.frontier_peak if self.result else 0}",
            f"Solution length: {self.result.path_length if self.result else 0}",
        ]
        draw_stats_block(surface, fonts, "Demo Stats", lines, stats_rect)
        panel_card(surface, legend_rect)
        draw_panel_title(surface, fonts, legend_rect, "Legend", inset=14)
        legend_items = [
            (ACCENT, "Current"),
            (SUCCESS, "On path"),
            ((145, 146, 152), "Explored"),
        ]
        for idx, (color, label) in enumerate(legend_items):
            cy = legend_rect.y + 60 + idx * 26
            pygame.draw.circle(surface, color, (legend_rect.x + 22, cy + 8), 6)
            draw_text(surface, fonts["small"], label, TEXT, (legend_rect.x + 38, cy))

        panel_card(surface, message_rect)
        message = ellipsize_text(fonts["small"], self.message, message_rect.width - 36)
        draw_text(surface, fonts["small"], message, TEXT, (message_rect.x + 18, message_rect.y + 16))

        for button in self.buttons:
            button.draw(surface, fonts, mouse_pos)
