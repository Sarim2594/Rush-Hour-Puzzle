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
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Button,
    create_fonts,
    draw_background,
    draw_text,
    ellipsize_text,
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
        draw_text(surface, fonts["title"], "Rush Hour Puzzle Solver", TEXT, (100, 90))
        draw_text(
            surface,
            fonts["small"],
            "A* search, interactive play, demo mode, and a custom puzzle editor.",
            MUTED,
            (100, 142),
        )

        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            button.draw(surface, fonts, mouse_pos)

        card = pygame.Rect(460, 220, 620, 430)
        panel_card(surface, card)
        draw_text(surface, fonts["heading"], "How To Use", TEXT, (card.x + 24, card.y + 20))
        underline = pygame.Rect(card.x + 24, card.y + 50, card.width - 48, 2)
        pygame.draw.rect(surface, ACCENT, underline)

        lines = [
            ("Play", "Solve a puzzle yourself with hints and move tracking."),
            ("Visual Demo", "Watch A* explore states and replay the best path."),
            ("Editor", "Create your own 6x6 layouts and save as JSON."),
            ("History", "Review attempts, best times, and solved runs."),
        ]
        y = card.y + 80
        for label, desc in lines:
            draw_text(surface, fonts["heading"], label, ACCENT_DARK, (card.x + 28, y))
            draw_text(surface, fonts["small"], desc, TEXT, (card.x + 28, y + 28))
            y += 78


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

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        draw_background(surface)
        _, screen_h = surface.get_size()
        draw_text(surface, fonts["title"], "Solve History", TEXT, (60, 50))

        entries = self.history.get("entries", [])
        solved_entries = [entry for entry in entries if entry.get("solved")]

        summary_rect = pygame.Rect(60, 130, 340, 180)
        panel_card(surface, summary_rect)
        draw_text(surface, fonts["heading"], "Overall Stats", TEXT, (summary_rect.x + 18, summary_rect.y + 14))
        pygame.draw.rect(surface, ACCENT, pygame.Rect(summary_rect.x + 18, summary_rect.y + 44, summary_rect.width - 36, 1))
        summary_lines = [
            f"Total attempts: {len(entries)}",
            f"Solved runs: {len(solved_entries)}",
            f"Puzzles attempted: {len(self.history.get('puzzles', {}))}",
        ]
        for index, line in enumerate(summary_lines):
            draw_text(surface, fonts["body"], line, TEXT, (summary_rect.x + 18, summary_rect.y + 62 + index * 32))

        puzzles_rect = pygame.Rect(430, 130, 690, 260)
        panel_card(surface, puzzles_rect)
        draw_text(surface, fonts["heading"], "Per Puzzle Bests", TEXT, (puzzles_rect.x + 18, puzzles_rect.y + 14))
        pygame.draw.rect(surface, ACCENT, pygame.Rect(puzzles_rect.x + 18, puzzles_rect.y + 44, puzzles_rect.width - 36, 1))
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

        row_bottom = max(summary_rect.bottom, puzzles_rect.bottom)
        recent_top = row_bottom + 20
        bottom_reserved = 74  # back button + margin
        recent_height = max(220, screen_h - recent_top - bottom_reserved)
        recent_rect = pygame.Rect(60, recent_top, 1060, recent_height)
        panel_card(surface, recent_rect)
        draw_text(surface, fonts["heading"], "Recent Attempts", TEXT, (recent_rect.x + 18, recent_rect.y + 14))
        pygame.draw.rect(surface, ACCENT, pygame.Rect(recent_rect.x + 18, recent_rect.y + 44, recent_rect.width - 36, 1))
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

        self.back_button.rect.y = min(screen_h - self.back_button.rect.height - 12, recent_rect.bottom + 12)
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
        start_x, start_y = 60, 170
        width, height = 330, 130
        gap_x, gap_y = 26, 26
        for index, board in enumerate(self.boards):
            row = index // 3
            col = index % 3
            rect = pygame.Rect(start_x + col * (width + gap_x), start_y + row * (height + gap_y), width, height)
            self.card_rects.append((rect, board))

    def handle_event(self, event: pygame.event.Event) -> tuple[str, Board] | str | None:
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
        title = f"Choose A Puzzle For {self.mode_kind.title()}"
        draw_text(surface, fonts["title"], title, TEXT, (60, 50))
        draw_text(surface, fonts["small"], "Built-in and saved custom puzzles appear here.", MUTED, (60, 120))
        mouse_pos = pygame.mouse.get_pos()

        for rect, board in self.card_rects:
            hovered = rect.collidepoint(mouse_pos)
            panel_card(surface, rect)
            if hovered:
                pygame.draw.rect(surface, ACCENT, rect, width=2, border_radius=10)
            draw_text(surface, fonts["heading"], board.metadata.get("name", "Puzzle"), TEXT, (rect.x + 18, rect.y + 18))
            draw_text(surface, fonts["small"], f"ID: {board.metadata.get('id', '-')}", MUTED, (rect.x + 18, rect.y + 60))
            draw_text(
                surface,
                fonts["small"],
                f"Difficulty: {board.metadata.get('difficulty', 'Custom')}",
                MUTED,
                (rect.x + 18, rect.y + 88),
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
