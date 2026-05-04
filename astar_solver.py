from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import time
from itertools import count

from board import Board, Move


@dataclass(slots=True)
class SolveResult:
    """
    Contains the outcome and statistics of an A* search execution.
    """
    solved: bool
    moves: list[Move]
    explored_states: int
    elapsed_time: float
    path_length: int
    frontier_peak: int = 0
    exploration_order: tuple[Board, ...] = field(default_factory=tuple)
    parent_by_key: dict[tuple[tuple[str, int, int], ...], tuple[tuple[str, int, int], ...] | None] = field(
        default_factory=dict
    )
    depth_by_key: dict[tuple[tuple[str, int, int], ...], int] = field(default_factory=dict)


def blocking_heuristic(board: Board) -> int:
    """
    Calculates a heuristic value for A* based on the number of vehicles blocking the red car from the exit.
    """
    if board.is_goal():
        return 0
    return len(board.blocking_vehicles()) + 1


def reconstruct_path(
    came_from: dict[tuple[tuple[str, int, int], ...], tuple[tuple[tuple[str, int, int], ...], Move]],
    goal_state: Board,
) -> list[Move]:
    path: list[Move] = []
    current_key = goal_state.state_key()
    while current_key in came_from:
        previous_key, move = came_from[current_key]
        path.append(move)
        current_key = previous_key
    path.reverse()
    return path


def solve_astar(board: Board, *, capture_exploration: bool = False) -> SolveResult:
    """
    Solves the given Rush Hour board using the A* search algorithm.
    Optionally captures the exploration order for visualization purposes.
    """
    start_time = time.perf_counter()
    start_key = board.state_key()

    if board.is_goal():
        return SolveResult(
            solved=True,
            moves=[],
            explored_states=1,
            elapsed_time=time.perf_counter() - start_time,
            path_length=0,
            frontier_peak=1,
            exploration_order=(board,) if capture_exploration else (),
            parent_by_key={start_key: None},
            depth_by_key={start_key: 0},
        )

    open_set: list[tuple[int, int, int, Board]] = []
    sequence = count()
    heapq.heappush(open_set, (blocking_heuristic(board), 0, next(sequence), board))

    g_score = {start_key: 0}
    came_from: dict[
        tuple[tuple[str, int, int], ...],
        tuple[tuple[tuple[str, int, int], ...], Move],
    ] = {}
    boards_by_key = {start_key: board}
    parent_by_key = {start_key: None}
    depth_by_key = {start_key: 0}
    closed: set[tuple[tuple[str, int, int], ...]] = set()
    explored_states = 0
    frontier_peak = 1
    exploration: list[Board] = []

    while open_set:
        _, current_cost, _, current_board = heapq.heappop(open_set)
        current_key = current_board.state_key()
        if current_key in closed:
            continue

        closed.add(current_key)
        explored_states += 1
        if capture_exploration:
            exploration.append(current_board)

        if current_board.is_goal():
            moves = reconstruct_path(came_from, current_board)
            return SolveResult(
                solved=True,
                moves=moves,
                explored_states=explored_states,
                elapsed_time=time.perf_counter() - start_time,
                path_length=len(moves),
                frontier_peak=frontier_peak,
                exploration_order=tuple(exploration),
                parent_by_key=parent_by_key,
                depth_by_key=depth_by_key,
            )

        for move in current_board.get_legal_moves():
            neighbor = current_board.apply_move(move)
            neighbor_key = neighbor.state_key()
            tentative_g = current_cost + 1

            if tentative_g >= g_score.get(neighbor_key, float("inf")):
                continue

            came_from[neighbor_key] = (current_key, move)
            boards_by_key[neighbor_key] = neighbor
            parent_by_key[neighbor_key] = current_key
            depth_by_key[neighbor_key] = tentative_g
            g_score[neighbor_key] = tentative_g
            priority = tentative_g + blocking_heuristic(neighbor)
            heapq.heappush(open_set, (priority, tentative_g, next(sequence), neighbor))
            frontier_peak = max(frontier_peak, len(open_set))

    return SolveResult(
        solved=False,
        moves=[],
        explored_states=explored_states,
        elapsed_time=time.perf_counter() - start_time,
        path_length=0,
        frontier_peak=frontier_peak,
        exploration_order=tuple(exploration),
        parent_by_key=parent_by_key,
        depth_by_key=depth_by_key,
    )


def get_hint(board: Board) -> Move | None:
    result = solve_astar(board, capture_exploration=False)
    if not result.solved or not result.moves:
        return None
    return result.moves[0]
