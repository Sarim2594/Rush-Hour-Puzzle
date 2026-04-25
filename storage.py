from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from board import Board


BASE_DIR = Path(__file__).resolve().parent
PUZZLES_DIR = BASE_DIR / "puzzles"
CUSTOM_PUZZLES_DIR = BASE_DIR / "custom_puzzles"
DATA_DIR = BASE_DIR / "data"
HISTORY_PATH = DATA_DIR / "solve_history.json"
DIFFICULTY_ORDER = {
    "Easy": 0,
    "Medium": 1,
    "Hard": 2,
    "Custom": 3,
}


@dataclass(slots=True)
class HistoryEntry:
    timestamp: str
    puzzle_id: str
    solved: bool
    moves: int
    elapsed_seconds: float


def ensure_storage() -> None:
    PUZZLES_DIR.mkdir(exist_ok=True)
    CUSTOM_PUZZLES_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    if not HISTORY_PATH.exists():
        HISTORY_PATH.write_text(json.dumps({"puzzles": {}, "entries": []}, indent=2), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_board(path: Path) -> Board:
    return Board.from_dict(_load_json(path))


def load_puzzle_library() -> list[Board]:
    ensure_storage()
    boards: list[Board] = []
    for path in sorted(PUZZLES_DIR.glob("*.json")):
        boards.append(load_board(path))
    for path in sorted(CUSTOM_PUZZLES_DIR.glob("*.json")):
        boards.append(load_board(path))
    boards.sort(
        key=lambda board: (
            DIFFICULTY_ORDER.get(board.metadata.get("difficulty", "Custom"), 99),
            board.metadata.get("name", "").lower(),
        )
    )
    return boards


def save_custom_puzzle(board: Board, filename: str | None = None) -> Path:
    ensure_storage()
    safe_name = filename or board.metadata.get("id") or "custom_puzzle"
    target = CUSTOM_PUZZLES_DIR / f"{safe_name}.json"
    target.write_text(json.dumps(board.to_dict(), indent=2), encoding="utf-8")
    return target


def load_history() -> dict[str, Any]:
    ensure_storage()
    return _load_json(HISTORY_PATH)


def save_history(history: dict[str, Any]) -> None:
    ensure_storage()
    HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")


def record_solve(puzzle_id: str, solved: bool, moves: int, elapsed_seconds: float) -> dict[str, Any]:
    history = load_history()
    puzzle_history = history.setdefault("puzzles", {}).setdefault(
        puzzle_id,
        {
            "best_moves": None,
            "best_time": None,
            "last_result": None,
        },
    )

    entry = HistoryEntry(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        puzzle_id=puzzle_id,
        solved=solved,
        moves=moves,
        elapsed_seconds=round(elapsed_seconds, 3),
    )
    history.setdefault("entries", []).append(asdict(entry))
    puzzle_history["last_result"] = asdict(entry)

    if solved:
        if puzzle_history["best_moves"] is None or moves < puzzle_history["best_moves"]:
            puzzle_history["best_moves"] = moves
        if puzzle_history["best_time"] is None or elapsed_seconds < puzzle_history["best_time"]:
            puzzle_history["best_time"] = round(elapsed_seconds, 3)

    save_history(history)
    return history


def get_puzzle_history(puzzle_id: str) -> dict[str, Any]:
    history = load_history()
    puzzle_history = history.get("puzzles", {}).get(
        puzzle_id,
        {
            "best_moves": None,
            "best_time": None,
            "last_result": None,
        },
    )
    entries = [entry for entry in history.get("entries", []) if entry.get("puzzle_id") == puzzle_id]
    return {
        "summary": puzzle_history,
        "entries": entries,
    }
