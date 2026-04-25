from __future__ import annotations

from dataclasses import dataclass

import pygame

from board import Board
from demo_mode import DemoMode
from editor import EditorMode
from play_mode import PlayMode
from storage import ensure_storage, load_history, load_puzzle_library
from ui import (
    ACCENT,
    ACCENT_DARK,
    MUTED,
    TEXT,
    WARNING,
    Button,
    create_fonts,
    draw_background,
    draw_panel_title,
    draw_screen_title,
    draw_stats_block,
    draw_text,
    ellipsize_text,
    get_screen_chrome,
    layout_buttons_in_rect,
    measure_stats_block_height,
    measure_text_panel_height,
    panel_card,
)


@dataclass
class MenuScreen:
    def __post_init__(self) -> None:
        labels_actions = [
            ("Play", "play"),
            ("Visual Demo", "demo"),
            ("Editor", "editor"),
            ("Solve History", "history"),
            ("Quit", "quit"),
        ]
        self.buttons: list[Button] = []
        for idx, (label, action) in enumerate(labels_actions):
            fill = WARNING if action == "quit" else ACCENT
            self.buttons.append(
                Button(
                    label=label,
                    rect=pygame.Rect(100, 220 + idx * 78, 300, 60),
                    action=action,
                    fill=fill,
                )
            )

    def _layout(self, surface: pygame.Surface) -> dict[str, pygame.Rect]:
        width, height = surface.get_size()
        chrome = get_screen_chrome(surface)
        content_h = chrome.content_bottom - chrome.content_top
        stacked = width < 1100 or width / max(1, height) < 1.4
        if stacked:
            left_h = max(280, min(int(content_h * 0.44), 360))
            left_rect = pygame.Rect(chrome.margin, chrome.content_top, width - chrome.margin * 2, left_h)
            card_rect = pygame.Rect(
                chrome.margin,
                left_rect.bottom + chrome.gap,
                width - chrome.margin * 2,
                chrome.content_bottom - left_rect.bottom - chrome.gap,
            )
        else:
            left_w = max(300, min(360, int(width * 0.3)))
            left_rect = pygame.Rect(chrome.margin, chrome.content_top, left_w, content_h)
            card_rect = pygame.Rect(
                left_rect.right + chrome.gap,
                chrome.content_top,
                width - left_rect.right - chrome.gap - chrome.margin,
                content_h,
            )
        buttons_rect = pygame.Rect(left_rect.x + 18, left_rect.y + 74, left_rect.width - 36, left_rect.height - 96)
        return {"left": left_rect, "card": card_rect, "buttons": buttons_rect}

    def handle_event(self, event: pygame.event.Event) -> str | None:
        for button in self.buttons:
            action = button.handle_event(event)
            if action:
                return action
        return None

    def update(self, dt: float) -> None:
        return None

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        draw_background(surface)
        draw_screen_title(
            surface,
            fonts,
            "Rush Hour Puzzle Solver",
            "A polished toolkit for interactive play, A* visualization, editing, and solve history.",
        )
        layout = self._layout(surface)
        left_rect = layout["left"]
        buttons_rect = layout["buttons"]
        card = layout["card"]
        mouse_pos = pygame.mouse.get_pos()
        panel_card(surface, left_rect)
        draw_panel_title(surface, fonts, left_rect, "Modes")
        panel_card(surface, card)
        draw_panel_title(surface, fonts, card, "How To Use", inset=24)

        lines = [
            ("Play", "Solve a puzzle yourself with hints and move tracking."),
            ("Visual Demo", "Watch A* explore states and replay the best path."),
            ("Editor", "Create your own 6x6 layouts and save as JSON."),
            ("History", "Review attempts, best times, and solved runs."),
        ]
        y = card.y + 78
        for label, desc in lines:
            draw_text(surface, fonts["heading"], label, ACCENT_DARK, (card.x + 28, y))
            draw_text(surface, fonts["small"], desc, TEXT, (card.x + 28, y + 28))
            y += 78

        layout_buttons_in_rect(self.buttons, buttons_rect, min_width=140, max_width=220, gap=12)
        for button in self.buttons:
            button.draw(surface, fonts, mouse_pos)


@dataclass
class SolveHistoryScreen:
    def __post_init__(self) -> None:
        self.back_button = Button("Back", pygame.Rect(60, 680, 120, 48), "back", fill=ACCENT)
        self.puzzle_scroll = 0
        self.recent_scroll = 0
        self._puzzles_view_rect = pygame.Rect(0, 0, 0, 0)
        self._recent_view_rect = pygame.Rect(0, 0, 0, 0)
        self.refresh()

    def refresh(self) -> None:
        self.history = load_history()
        boards = load_puzzle_library()
        self.board_names = {board.metadata.get("id", "custom"): board.metadata.get("name", "Puzzle") for board in boards}
        self.puzzle_items = sorted(self.history.get("puzzles", {}).items())
        self.puzzle_scroll = 0
        self.recent_scroll = 0

    @staticmethod
    def _max_scroll(item_count: int, line_height: int, view_height: int) -> int:
        content_height = item_count * line_height
        return max(0, content_height - view_height)

    def _scroll_history(self, amount: int, over_puzzles: bool, entries_count: int) -> None:
        if over_puzzles:
            max_scroll = self._max_scroll(len(self.puzzle_items), 34, self._puzzles_view_rect.height)
            self.puzzle_scroll = max(0, min(max_scroll, self.puzzle_scroll + amount))
        else:
            max_scroll = self._max_scroll(entries_count, 32, self._recent_view_rect.height)
            self.recent_scroll = max(0, min(max_scroll, self.recent_scroll + amount))

    @staticmethod
    def _draw_scrollbar(
        surface: pygame.Surface,
        track_rect: pygame.Rect,
        content_height: int,
        view_height: int,
        scroll: int,
    ) -> None:
        if content_height <= view_height:
            return
        pygame.draw.rect(surface, (225, 222, 214), track_rect, border_radius=4)
        thumb_h = max(24, int(track_rect.height * (view_height / content_height)))
        max_thumb_y = track_rect.height - thumb_h
        thumb_y = track_rect.y
        if max_thumb_y > 0:
            thumb_y += int((scroll / max(1, content_height - view_height)) * max_thumb_y)
        thumb_rect = pygame.Rect(track_rect.x + 1, thumb_y, track_rect.width - 2, thumb_h)
        pygame.draw.rect(surface, (168, 165, 156), thumb_rect, border_radius=4)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        action = self.back_button.handle_event(event)
        if action:
            return action
        entries = self.history.get("entries", [])
        recent_entries = entries[::-1]
        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self._puzzles_view_rect.collidepoint(mouse_pos):
                self._scroll_history(-event.y * 24, over_puzzles=True, entries_count=len(recent_entries))
            elif self._recent_view_rect.collidepoint(mouse_pos):
                self._scroll_history(-event.y * 24, over_puzzles=False, entries_count=len(recent_entries))
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in {4, 5}:
            mouse_pos = event.pos
            direction = -24 if event.button == 4 else 24
            if self._puzzles_view_rect.collidepoint(mouse_pos):
                self._scroll_history(direction, over_puzzles=True, entries_count=len(recent_entries))
            elif self._recent_view_rect.collidepoint(mouse_pos):
                self._scroll_history(direction, over_puzzles=False, entries_count=len(recent_entries))
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "back"
        return None

    def update(self, dt: float) -> None:
        return None

    def _layout(self, surface: pygame.Surface) -> dict[str, pygame.Rect]:
        width, height = surface.get_size()
        chrome = get_screen_chrome(surface)
        content_w = width - chrome.margin * 2
        stacked = width < 1140 or width / max(1, height) < 1.5
        stats_w = max(300, min(360, int(content_w * 0.31)))
        top_row_h = max(
            measure_stats_block_height(3),
            measure_text_panel_height(5, top_padding=64, line_gap=34, bottom_padding=18),
        )
        if stacked:
            summary_rect = pygame.Rect(chrome.margin, chrome.content_top, content_w, measure_stats_block_height(3))
            puzzles_rect = pygame.Rect(
                chrome.margin,
                summary_rect.bottom + chrome.gap,
                content_w,
                max(190, top_row_h - 24),
            )
        else:
            summary_rect = pygame.Rect(chrome.margin, chrome.content_top, stats_w, top_row_h)
            puzzles_rect = pygame.Rect(
                summary_rect.right + chrome.gap,
                chrome.content_top,
                width - summary_rect.right - chrome.gap - chrome.margin,
                top_row_h,
            )
        recent_top = puzzles_rect.bottom + chrome.gap
        recent_h = max(220, height - recent_top - 48 - chrome.gap - chrome.margin)
        recent_rect = pygame.Rect(chrome.margin, recent_top, content_w, recent_h)
        back_rect = pygame.Rect(chrome.margin, recent_rect.bottom + chrome.gap, 120, 48)
        return {
            "summary": summary_rect,
            "puzzles": puzzles_rect,
            "recent": recent_rect,
            "back": back_rect,
        }

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        draw_background(surface)
        layout = self._layout(surface)
        summary_rect = layout["summary"]
        puzzles_rect = layout["puzzles"]
        recent_rect = layout["recent"]
        self.back_button.rect = layout["back"]
        draw_screen_title(
            surface,
            fonts,
            "Solve History",
            "Best runs and recent attempts in one consistent overview.",
        )

        entries = self.history.get("entries", [])
        solved_entries = [entry for entry in entries if entry.get("solved")]

        summary_lines = [
            f"Total attempts: {len(entries)}",
            f"Solved runs: {len(solved_entries)}",
            f"Puzzles attempted: {len(self.history.get('puzzles', {}))}",
        ]
        draw_stats_block(surface, fonts, "Overall Stats", summary_lines, summary_rect)
        panel_card(surface, puzzles_rect)
        draw_panel_title(surface, fonts, puzzles_rect, "Per Puzzle Bests")
        puzzles_view_rect = pygame.Rect(puzzles_rect.x + 18, puzzles_rect.y + 64, puzzles_rect.width - 36, puzzles_rect.height - 76)
        self._puzzles_view_rect = puzzles_view_rect
        if not self.puzzle_items:
            draw_text(surface, fonts["small"], "No solve history recorded yet.", MUTED, (puzzles_rect.x + 18, puzzles_rect.y + 64))
        line_h_puzzles = 34
        content_h_puzzles = len(self.puzzle_items) * line_h_puzzles
        self.puzzle_scroll = max(0, min(self.puzzle_scroll, self._max_scroll(len(self.puzzle_items), line_h_puzzles, puzzles_view_rect.height)))
        old_clip = surface.get_clip()
        surface.set_clip(puzzles_view_rect)
        for index, (puzzle_id, data) in enumerate(self.puzzle_items):
            name = self.board_names.get(puzzle_id, puzzle_id)
            best_moves = data.get("best_moves") if data.get("best_moves") is not None else "-"
            best_time = data.get("best_time")
            best_time_text = "-" if best_time is None else f"{int(best_time) // 60:02d}:{int(best_time) % 60:02d}"
            line = f"{name}: best moves {best_moves}, best time {best_time_text}"
            fitted = ellipsize_text(fonts["small"], line, puzzles_view_rect.width - 14)
            y = puzzles_view_rect.y + index * line_h_puzzles - self.puzzle_scroll
            draw_text(surface, fonts["small"], fitted, TEXT, (puzzles_view_rect.x, y))
        surface.set_clip(old_clip)
        self._draw_scrollbar(
            surface,
            pygame.Rect(puzzles_rect.right - 14, puzzles_view_rect.y, 8, puzzles_view_rect.height),
            content_h_puzzles,
            puzzles_view_rect.height,
            self.puzzle_scroll,
        )

        panel_card(surface, recent_rect)
        draw_panel_title(surface, fonts, recent_rect, "Recent Attempts")
        recent_entries = entries[::-1]
        recent_view_rect = pygame.Rect(recent_rect.x + 18, recent_rect.y + 64, recent_rect.width - 36, recent_rect.height - 76)
        self._recent_view_rect = recent_view_rect
        if not recent_entries:
            draw_text(surface, fonts["small"], "No attempts recorded yet.", MUTED, (recent_rect.x + 18, recent_rect.y + 64))
        line_h_recent = 32
        content_h_recent = len(recent_entries) * line_h_recent
        self.recent_scroll = max(0, min(self.recent_scroll, self._max_scroll(len(recent_entries), line_h_recent, recent_view_rect.height)))
        old_clip = surface.get_clip()
        surface.set_clip(recent_view_rect)
        for index, entry in enumerate(recent_entries):
            name = self.board_names.get(entry.get("puzzle_id", ""), entry.get("puzzle_id", "Puzzle"))
            color = ACCENT_DARK if entry.get("solved") else MUTED
            line = (
                f"{entry.get('timestamp', '-')}: {name} | "
                f"{'Solved' if entry.get('solved') else 'Attempt'} | "
                f"Moves {entry.get('moves', '-')} | "
                f"Time {int(entry.get('elapsed_seconds', 0)) // 60:02d}:{int(entry.get('elapsed_seconds', 0)) % 60:02d}"
            )
            fitted = ellipsize_text(fonts["small"], line, recent_view_rect.width - 14)
            y = recent_view_rect.y + index * line_h_recent - self.recent_scroll
            draw_text(surface, fonts["small"], fitted, color, (recent_view_rect.x, y))
        surface.set_clip(old_clip)
        self._draw_scrollbar(
            surface,
            pygame.Rect(recent_rect.right - 14, recent_view_rect.y, 8, recent_view_rect.height),
            content_h_recent,
            recent_view_rect.height,
            self.recent_scroll,
        )

        self.back_button.draw(surface, fonts, pygame.mouse.get_pos())


@dataclass
class PuzzleSelectScreen:
    mode_kind: str

    def __post_init__(self) -> None:
        self.back_button = Button("Back", pygame.Rect(60, 680, 120, 48), "back", fill=ACCENT)
        self.refresh()

    def refresh(self) -> None:
        self.boards = load_puzzle_library()
        self.card_rects: list[tuple[pygame.Rect, Board]] = []

    def _layout(self, surface: pygame.Surface) -> dict[str, pygame.Rect | int]:
        width, height = surface.get_size()
        chrome = get_screen_chrome(surface)
        footer_h = 48
        available_w = width - chrome.margin * 2
        if available_w >= 1320:
            cols = 4
        elif available_w >= 880:
            cols = 3
        else:
            cols = 2
        card_gap = chrome.gap
        card_w = (available_w - card_gap * (cols - 1)) // cols
        card_h = 150
        grid_top = chrome.content_top
        grid_bottom = height - chrome.margin - footer_h - chrome.gap
        usable_h = max(card_h, grid_bottom - grid_top)
        rows = max(1, usable_h // (card_h + card_gap))
        return {
            "grid_top": grid_top,
            "card_w": card_w,
            "card_h": card_h,
            "card_gap": card_gap,
            "cols": cols,
            "rows": rows,
            "back_y": height - chrome.margin - footer_h,
            "margin_x": chrome.margin,
        }

    def _sync_card_rects(self, surface: pygame.Surface) -> None:
        layout = self._layout(surface)
        margin_x = int(layout["margin_x"])
        start_y = int(layout["grid_top"])
        width = int(layout["card_w"])
        height = int(layout["card_h"])
        gap = int(layout["card_gap"])
        cols = int(layout["cols"])
        self.card_rects = []
        for index, board in enumerate(self.boards):
            row = index // cols
            col = index % cols
            rect = pygame.Rect(margin_x + col * (width + gap), start_y + row * (height + gap), width, height)
            self.card_rects.append((rect, board))

    def handle_event(self, event: pygame.event.Event) -> tuple[str, Board] | str | None:
        surface = pygame.display.get_surface()
        if surface is not None and not self.card_rects:
            self._sync_card_rects(surface)
        action = self.back_button.handle_event(event)
        if action:
            return "back"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, board in self.card_rects:
                if rect.collidepoint(event.pos):
                    return ("select", board)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "back"
        return None

    def update(self, dt: float) -> None:
        return None

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        draw_background(surface)
        layout = self._layout(surface)
        self._sync_card_rects(surface)
        self.back_button.rect.y = int(layout["back_y"])
        title = f"Choose A Puzzle For {self.mode_kind.title()}"
        draw_screen_title(
            surface,
            fonts,
            title,
            "Built-in and saved custom puzzles appear here.",
        )
        mouse_pos = pygame.mouse.get_pos()

        for rect, board in self.card_rects:
            hovered = rect.collidepoint(mouse_pos)
            panel_card(surface, rect)
            if hovered:
                pygame.draw.rect(surface, ACCENT, rect, width=2, border_radius=10)
            draw_text(surface, fonts["heading"], ellipsize_text(fonts["heading"], board.metadata.get("name", "Puzzle"), rect.width - 36), TEXT, (rect.x + 18, rect.y + 18))
            draw_text(surface, fonts["small"], f"ID: {board.metadata.get('id', '-')}", MUTED, (rect.x + 18, rect.y + 64))
            draw_text(
                surface,
                fonts["small"],
                f"Difficulty: {board.metadata.get('difficulty', 'Custom')}",
                MUTED,
                (rect.x + 18, rect.y + 92),
            )

        self.back_button.draw(surface, fonts, mouse_pos)


def run() -> int:
    ensure_storage()
    pygame.init()
    pygame.display.set_caption("Rush Hour Puzzle Solver")
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    clock = pygame.time.Clock()
    fonts = create_fonts()

    current_screen: object = MenuScreen()

    while True:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return 0

            result = current_screen.handle_event(event)
            if result is None:
                continue

            if isinstance(current_screen, MenuScreen):
                if result == "play":
                    current_screen = PuzzleSelectScreen("play")
                elif result == "demo":
                    current_screen = PuzzleSelectScreen("demo")
                elif result == "editor":
                    current_screen = EditorMode()
                elif result == "history":
                    current_screen = SolveHistoryScreen()
                elif result == "quit":
                    pygame.quit()
                    return 0
            elif isinstance(current_screen, PuzzleSelectScreen):
                if result == "back":
                    current_screen = MenuScreen()
                elif isinstance(result, tuple) and result[0] == "select":
                    board = result[1]
                    if current_screen.mode_kind == "play":
                        current_screen = PlayMode(
                            initial_board=board,
                            puzzle_id=board.metadata.get("id", "custom"),
                            puzzle_name=board.metadata.get("name", "Rush Hour"),
                        )
                    else:
                        current_screen = DemoMode(
                            initial_board=board,
                            puzzle_name=board.metadata.get("name", "Rush Hour"),
                        )
            else:
                if result == "back":
                    current_screen = MenuScreen()

        current_screen.update(dt)
        current_screen.draw(screen, fonts)
        pygame.display.flip()


if __name__ == "__main__":
    raise SystemExit(run())
