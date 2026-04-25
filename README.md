# Rush Hour Puzzle Solver

A Python + Pygame Rush Hour puzzle solver and player built around an `A*` search with a blocking heuristic.

## Features

- Built-in Rush Hour puzzles across multiple difficulty levels
- Visual demo mode that replays search exploration and the final solution
- Normal play mode with hints, move counter, and timer
- Puzzle editor with JSON save/load support
- Local solve-history tracking in JSON
- Pytest suite for the core model, solver, persistence, and smoke behavior

## Setup

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Controls

- Main menu: choose Play, Visual Demo, Editor, or Quit
- Puzzle list: click a puzzle card to start
- Play mode:
  - Click a vehicle to select it
  - Use arrow buttons or keyboard arrows to move the selected vehicle
  - Click `Hint` for the next optimal move
  - Click `Solve` to watch the optimal solution from the current state
- Demo mode:
  - Click `Start Demo`
  - Adjust playback speed with the on-screen buttons
- Editor mode:
  - Select an orientation and vehicle length
  - Click grid cells to place vehicles
  - Select an existing vehicle, then move or delete it
  - Save the puzzle when validation succeeds

## Project Structure

- `board.py`: board model, moves, validation, serialization
- `astar_solver.py`: `A*` solver and heuristic
- `storage.py`: puzzle library and history persistence
- `ui.py`: shared rendering, widgets, colors, animation helpers
- `play_mode.py`: interactive player mode with hints
- `demo_mode.py`: solver visualization mode
- `editor.py`: puzzle editor
- `main.py`: application entrypoint and state machine
- `puzzles/`: bundled JSON puzzles
- `tests/`: pytest suite
