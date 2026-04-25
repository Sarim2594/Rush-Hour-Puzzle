import json

import storage
from board import Board


def test_history_file_creation_and_update(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "PUZZLES_DIR", tmp_path / "puzzles")
    monkeypatch.setattr(storage, "CUSTOM_PUZZLES_DIR", tmp_path / "custom")
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(storage, "HISTORY_PATH", tmp_path / "data" / "solve_history.json")

    storage.ensure_storage()
    assert storage.HISTORY_PATH.exists()

    history = storage.record_solve("sample", True, 7, 12.34)
    assert history["puzzles"]["sample"]["best_moves"] == 7
    assert history["entries"][-1]["solved"] is True

    puzzle_history = storage.get_puzzle_history("sample")
    assert puzzle_history["summary"]["best_moves"] == 7
    assert len(puzzle_history["entries"]) == 1


def test_custom_puzzle_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "PUZZLES_DIR", tmp_path / "puzzles")
    monkeypatch.setattr(storage, "CUSTOM_PUZZLES_DIR", tmp_path / "custom")
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(storage, "HISTORY_PATH", tmp_path / "data" / "solve_history.json")

    board = Board.from_dict(
        {
            "id": "custom_case",
            "name": "Custom Case",
            "vehicles": [
                {"id": "X", "row": 2, "col": 0, "length": 2, "orientation": "H", "is_red": True},
                {"id": "A", "row": 0, "col": 2, "length": 3, "orientation": "V"},
            ],
        }
    )

    target = storage.save_custom_puzzle(board, "custom_case")
    assert target.exists()

    loaded = storage.load_board(target)
    assert loaded == board
    assert json.loads(target.read_text())["id"] == "custom_case"
