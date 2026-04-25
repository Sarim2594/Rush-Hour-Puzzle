from astar_solver import blocking_heuristic, get_hint, solve_astar
from board import Board


def simple_puzzle() -> Board:
    return Board.from_dict(
        {
            "id": "solver_case",
            "name": "Solver Case",
            "vehicles": [
                {"id": "X", "row": 2, "col": 1, "length": 2, "orientation": "H", "is_red": True},
                {"id": "A", "row": 0, "col": 0, "length": 2, "orientation": "V"},
                {"id": "B", "row": 0, "col": 3, "length": 3, "orientation": "V"},
            ],
        }
    )


def test_solver_finds_optimal_path() -> None:
    board = simple_puzzle()
    result = solve_astar(board)
    assert result.solved is True
    assert result.path_length == 2

    replay = board
    for move in result.moves:
        replay = replay.apply_move(move)
    assert replay.is_goal()


def test_hint_matches_first_optimal_move() -> None:
    board = simple_puzzle()
    result = solve_astar(board)
    hint = get_hint(board)
    assert hint == result.moves[0]


def test_goal_board_returns_empty_solution() -> None:
    board = Board.from_dict(
        {
            "id": "goal",
            "name": "Goal",
            "vehicles": [
                {"id": "X", "row": 2, "col": 4, "length": 2, "orientation": "H", "is_red": True},
                {"id": "A", "row": 0, "col": 0, "length": 2, "orientation": "V"},
            ],
        }
    )
    result = solve_astar(board)
    assert result.solved is True
    assert result.moves == []
    assert result.path_length == 0


def test_blocking_heuristic_is_zero_at_goal() -> None:
    board = Board.from_dict(
        {
            "id": "goal",
            "name": "Goal",
            "vehicles": [
                {"id": "X", "row": 2, "col": 4, "length": 2, "orientation": "H", "is_red": True},
                {"id": "A", "row": 0, "col": 0, "length": 2, "orientation": "V"},
            ],
        }
    )
    assert blocking_heuristic(board) == 0


def test_capture_exploration_returns_expanded_states() -> None:
    board = simple_puzzle()
    result = solve_astar(board, capture_exploration=True)
    assert result.exploration_order
    assert result.exploration_order[0] == board
