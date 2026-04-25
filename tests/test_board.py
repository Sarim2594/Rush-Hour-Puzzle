import pytest

from board import Board, Move, Vehicle


def sample_board() -> Board:
    return Board.from_dict(
        {
            "id": "sample",
            "name": "Sample",
            "vehicles": [
                {"id": "X", "row": 2, "col": 1, "length": 2, "orientation": "H", "is_red": True},
                {"id": "A", "row": 0, "col": 0, "length": 3, "orientation": "V"},
                {"id": "B", "row": 0, "col": 4, "length": 2, "orientation": "V"},
                {"id": "C", "row": 3, "col": 0, "length": 2, "orientation": "H"},
            ],
        }
    )


def test_board_occupancy_and_round_trip() -> None:
    board = sample_board()
    occupancy = board.occupancy()
    assert occupancy[(2, 1)] == "X"
    assert occupancy[(1, 0)] == "A"
    assert Board.from_dict(board.to_dict()) == board


def test_invalid_vehicle_overlap_is_rejected() -> None:
    with pytest.raises(ValueError):
        Board.from_dict(
            {
                "id": "bad",
                "name": "Bad",
                "vehicles": [
                    {"id": "X", "row": 2, "col": 1, "length": 2, "orientation": "H", "is_red": True},
                    {"id": "A", "row": 2, "col": 2, "length": 2, "orientation": "V"},
                ],
            }
        )


def test_legal_moves_include_horizontal_and_vertical_motion() -> None:
    board = sample_board()
    moves = {(move.vehicle_id, move.distance) for move in board.get_legal_moves()}
    assert ("X", 1) in moves
    assert ("B", 1) in moves
    assert ("C", 1) in moves


def test_apply_move_preserves_validity() -> None:
    board = sample_board()
    moved = board.apply_move(Move("X", 1))
    assert moved.get_vehicle("X").col == 2
    assert moved != board
    assert moved.can_apply_move(Move("B", 1))


def test_goal_detection_and_hashing() -> None:
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
    assert board.is_goal()
    assert hash(board) == hash(Board.from_dict(board.to_dict()))


def test_illegal_move_is_rejected() -> None:
    board = sample_board()
    with pytest.raises(ValueError):
        board.apply_move(Move("A", 2))
