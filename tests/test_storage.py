import json
import tempfile
from pathlib import Path
import pytest

import storage
from board import Board

@pytest.fixture
def custom_tmp_path():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def test_history_file_creation_and_update(custom_tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "PUZZLES_DIR", custom_tmp_path / "puzzles")
    monkeypatch.setattr(storage, "CUSTOM_PUZZLES_DIR", custom_tmp_path / "custom")
    monkeypatch.setattr(storage, "DATA_DIR", custom_tmp_path / "data")
    monkeypatch.setattr(storage, "HISTORY_PATH", custom_tmp_path / "data" / "solve_history.json")

    storage.ensure_storage()
    assert storage.HISTORY_PATH.exists()

    history = storage.record_solve("sample", True, 7, 12.34)
    assert history["puzzles"]["sample"]["best_moves"] == 7
    assert history["entries"][-1]["solved"] is True

    puzzle_history = storage.get_puzzle_history("sample")
    assert puzzle_history["summary"]["best_moves"] == 7
    assert len(puzzle_history["entries"]) == 1


def test_custom_puzzle_round_trip(custom_tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "PUZZLES_DIR", custom_tmp_path / "puzzles")
    monkeypatch.setattr(storage, "CUSTOM_PUZZLES_DIR", custom_tmp_path / "custom")
    monkeypatch.setattr(storage, "DATA_DIR", custom_tmp_path / "data")
    monkeypatch.setattr(storage, "HISTORY_PATH", custom_tmp_path / "data" / "solve_history.json")

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


def test_puzzle_library_is_sorted_by_difficulty_then_name(custom_tmp_path, monkeypatch) -> None:
    puzzles_dir = custom_tmp_path / "puzzles"
    custom_dir = custom_tmp_path / "custom"
    data_dir = custom_tmp_path / "data"
    monkeypatch.setattr(storage, "PUZZLES_DIR", puzzles_dir)
    monkeypatch.setattr(storage, "CUSTOM_PUZZLES_DIR", custom_dir)
    monkeypatch.setattr(storage, "DATA_DIR", data_dir)
    monkeypatch.setattr(storage, "HISTORY_PATH", data_dir / "solve_history.json")

    puzzles_dir.mkdir(parents=True)
    custom_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    (puzzles_dir / "hard.json").write_text(
        json.dumps(
            {
                "id": "hard_case",
                "name": "Zulu",
                "difficulty": "Hard",
                "vehicles": [
                    {"id": "X", "row": 2, "col": 0, "length": 2, "orientation": "H", "is_red": True},
                    {"id": "A", "row": 0, "col": 2, "length": 3, "orientation": "V"},
                ],
            }
        )
    )
    (puzzles_dir / "easy.json").write_text(
        json.dumps(
            {
                "id": "easy_case",
                "name": "Alpha",
                "difficulty": "Easy",
                "vehicles": [
                    {"id": "X", "row": 2, "col": 0, "length": 2, "orientation": "H", "is_red": True},
                    {"id": "A", "row": 0, "col": 2, "length": 3, "orientation": "V"},
                ],
            }
        )
    )
    (custom_dir / "custom.json").write_text(
        json.dumps(
            {
                "id": "custom_case",
                "name": "Beta",
                "vehicles": [
                    {"id": "X", "row": 2, "col": 0, "length": 2, "orientation": "H", "is_red": True},
                    {"id": "A", "row": 0, "col": 2, "length": 3, "orientation": "V"},
                ],
            }
        )
    )

    boards = storage.load_puzzle_library()
    assert [board.metadata.get("name") for board in boards] == ["Alpha", "Zulu", "Beta"]
