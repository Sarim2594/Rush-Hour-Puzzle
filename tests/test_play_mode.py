import time

from astar_solver import solve_astar
from board import Board
from play_mode import PlayMode
from ui import format_seconds


def simple_puzzle() -> Board:
    return Board.from_dict(
        {
            "id": "play_case",
            "name": "Play Case",
            "vehicles": [
                {"id": "X", "row": 2, "col": 1, "length": 2, "orientation": "H", "is_red": True},
                {"id": "A", "row": 0, "col": 0, "length": 2, "orientation": "V"},
                {"id": "B", "row": 0, "col": 3, "length": 3, "orientation": "V"},
            ],
        }
    )


def test_hint_plays_exactly_one_move() -> None:
    board = simple_puzzle()
    mode = PlayMode(board, "play_case", "Play Case")
    expected_move = solve_astar(board).moves[0]
    mode.apply_single_hint()

    assert mode.move_count == 1
    assert mode.board == board.apply_move(expected_move)
    assert mode.finished is False


def test_timer_stops_when_puzzle_is_solved() -> None:
    board = Board.from_dict(
        {
            "id": "already_one_move",
            "name": "Already One Move",
            "vehicles": [
                {"id": "X", "row": 2, "col": 3, "length": 2, "orientation": "H", "is_red": True},
                {"id": "A", "row": 0, "col": 0, "length": 2, "orientation": "V"},
            ],
        }
    )
    mode = PlayMode(board, "already_one_move", "Already One Move")
    mode.started_at = time.perf_counter() - 5

    mode.apply_single_hint()
    elapsed_after_solve = mode.elapsed()
    time.sleep(0.05)

    assert mode.finished is True
    assert mode.finished_at is not None
    assert mode.elapsed() == elapsed_after_solve


def test_format_seconds_uses_whole_seconds() -> None:
    assert format_seconds(65.9) == "01:05"
