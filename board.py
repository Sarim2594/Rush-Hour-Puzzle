from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


GRID_SIZE = 6
EXIT_ROW = 2
RED_VEHICLE_ID = "X"


@dataclass(frozen=True, slots=True)
class Move:
    vehicle_id: str
    distance: int

    def to_dict(self) -> dict:
        return {"vehicle_id": self.vehicle_id, "distance": self.distance}


@dataclass(frozen=True, slots=True)
class Vehicle:
    id: str
    row: int
    col: int
    length: int
    orientation: str
    is_red: bool = False

    def __post_init__(self) -> None:
        orientation = self.orientation.upper()
        object.__setattr__(self, "orientation", orientation)
        if self.length not in (2, 3):
            raise ValueError("Vehicle length must be 2 or 3.")
        if orientation not in {"H", "V"}:
            raise ValueError("Vehicle orientation must be 'H' or 'V'.")
        if self.row < 0 or self.col < 0:
            raise ValueError("Vehicle position must be non-negative.")

    @property
    def cells(self) -> tuple[tuple[int, int], ...]:
        if self.orientation == "H":
            return tuple((self.row, self.col + offset) for offset in range(self.length))
        return tuple((self.row + offset, self.col) for offset in range(self.length))

    def shifted(self, distance: int) -> "Vehicle":
        if self.orientation == "H":
            return Vehicle(
                id=self.id,
                row=self.row,
                col=self.col + distance,
                length=self.length,
                orientation=self.orientation,
                is_red=self.is_red,
            )
        return Vehicle(
            id=self.id,
            row=self.row + distance,
            col=self.col,
            length=self.length,
            orientation=self.orientation,
            is_red=self.is_red,
        )

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "row": self.row,
            "col": self.col,
            "length": self.length,
            "orientation": self.orientation,
        }
        if self.is_red:
            data["is_red"] = True
        return data


class Board:
    def __init__(self, vehicles: Iterable[Vehicle], *, metadata: dict | None = None):
        vehicle_list = list(vehicles)
        if not vehicle_list:
            raise ValueError("Board requires at least one vehicle.")
        self._vehicles = tuple(sorted(vehicle_list, key=lambda vehicle: vehicle.id))
        self.metadata = metadata.copy() if metadata else {}
        self._validate()

    def _validate(self) -> None:
        ids = [vehicle.id for vehicle in self._vehicles]
        if len(ids) != len(set(ids)):
            raise ValueError("Vehicle ids must be unique.")

        red_vehicles = [vehicle for vehicle in self._vehicles if vehicle.is_red or vehicle.id == RED_VEHICLE_ID]
        if len(red_vehicles) != 1:
            raise ValueError("Board must contain exactly one red vehicle.")

        seen_cells: dict[tuple[int, int], str] = {}
        for vehicle in self._vehicles:
            for row, col in vehicle.cells:
                if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
                    raise ValueError(f"Vehicle {vehicle.id} is out of bounds.")
                if (row, col) in seen_cells:
                    raise ValueError(
                        f"Vehicle {vehicle.id} overlaps with vehicle {seen_cells[(row, col)]}."
                    )
                seen_cells[(row, col)] = vehicle.id

        red_vehicle = self.red_vehicle
        if red_vehicle.orientation != "H" or red_vehicle.row != EXIT_ROW:
            raise ValueError("Red vehicle must be horizontal and start on the exit row.")

    @property
    def vehicles(self) -> tuple[Vehicle, ...]:
        return self._vehicles

    @property
    def red_vehicle(self) -> Vehicle:
        return next(vehicle for vehicle in self._vehicles if vehicle.is_red or vehicle.id == RED_VEHICLE_ID)

    def get_vehicle(self, vehicle_id: str) -> Vehicle:
        for vehicle in self._vehicles:
            if vehicle.id == vehicle_id:
                return vehicle
        raise KeyError(f"Unknown vehicle id: {vehicle_id}")

    def occupancy(self) -> dict[tuple[int, int], str]:
        occupied: dict[tuple[int, int], str] = {}
        for vehicle in self._vehicles:
            for cell in vehicle.cells:
                occupied[cell] = vehicle.id
        return occupied

    def state_key(self) -> tuple[tuple[str, int, int], ...]:
        return tuple((vehicle.id, vehicle.row, vehicle.col) for vehicle in self._vehicles)

    def is_goal(self) -> bool:
        red_vehicle = self.red_vehicle
        return red_vehicle.col + red_vehicle.length - 1 == GRID_SIZE - 1

    def can_apply_move(self, move: Move) -> bool:
        try:
            self.apply_move(move)
            return True
        except ValueError:
            return False

    def get_legal_moves(self) -> list[Move]:
        occupied = self.occupancy()
        legal_moves: list[Move] = []

        for vehicle in self._vehicles:
            if vehicle.orientation == "H":
                step = 1
                next_col = vehicle.col - 1
                while next_col >= 0 and (vehicle.row, next_col) not in occupied:
                    legal_moves.append(Move(vehicle.id, -step))
                    step += 1
                    next_col -= 1

                step = 1
                next_col = vehicle.col + vehicle.length
                while next_col < GRID_SIZE and (vehicle.row, next_col) not in occupied:
                    legal_moves.append(Move(vehicle.id, step))
                    step += 1
                    next_col += 1
            else:
                step = 1
                next_row = vehicle.row - 1
                while next_row >= 0 and (next_row, vehicle.col) not in occupied:
                    legal_moves.append(Move(vehicle.id, -step))
                    step += 1
                    next_row -= 1

                step = 1
                next_row = vehicle.row + vehicle.length
                while next_row < GRID_SIZE and (next_row, vehicle.col) not in occupied:
                    legal_moves.append(Move(vehicle.id, step))
                    step += 1
                    next_row += 1

        return legal_moves

    def apply_move(self, move: Move) -> "Board":
        if move.distance == 0:
            raise ValueError("Move distance cannot be zero.")

        vehicle = self.get_vehicle(move.vehicle_id)
        occupied = self.occupancy()
        for cell in vehicle.cells:
            occupied.pop(cell)

        if vehicle.orientation == "H":
            direction = 1 if move.distance > 0 else -1
            for offset in range(1, abs(move.distance) + 1):
                target_col = (
                    vehicle.col + vehicle.length - 1 + offset
                    if direction > 0
                    else vehicle.col - offset
                )
                if not (0 <= target_col < GRID_SIZE):
                    raise ValueError("Move would leave the board.")
                if (vehicle.row, target_col) in occupied:
                    raise ValueError("Move is blocked.")
        else:
            direction = 1 if move.distance > 0 else -1
            for offset in range(1, abs(move.distance) + 1):
                target_row = (
                    vehicle.row + vehicle.length - 1 + offset
                    if direction > 0
                    else vehicle.row - offset
                )
                if not (0 <= target_row < GRID_SIZE):
                    raise ValueError("Move would leave the board.")
                if (target_row, vehicle.col) in occupied:
                    raise ValueError("Move is blocked.")

        shifted_vehicle = vehicle.shifted(move.distance)
        new_vehicles = [shifted_vehicle if current.id == vehicle.id else current for current in self._vehicles]
        return Board(new_vehicles, metadata=self.metadata)

    def blocking_vehicles(self) -> list[str]:
        red_vehicle = self.red_vehicle
        occupied = self.occupancy()
        blockers: list[str] = []
        for col in range(red_vehicle.col + red_vehicle.length, GRID_SIZE):
            vehicle_id = occupied.get((red_vehicle.row, col))
            if vehicle_id and vehicle_id not in blockers:
                blockers.append(vehicle_id)
        return blockers

    def to_dict(self) -> dict:
        data = {
            "id": self.metadata.get("id", "custom_puzzle"),
            "name": self.metadata.get("name", "Custom Puzzle"),
            "vehicles": [vehicle.to_dict() for vehicle in self._vehicles],
        }
        if "difficulty" in self.metadata:
            data["difficulty"] = self.metadata["difficulty"]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Board":
        vehicles = [
            Vehicle(
                id=vehicle_data["id"],
                row=vehicle_data["row"],
                col=vehicle_data["col"],
                length=vehicle_data["length"],
                orientation=vehicle_data["orientation"],
                is_red=vehicle_data.get("is_red", vehicle_data["id"] == RED_VEHICLE_ID),
            )
            for vehicle_data in data["vehicles"]
        ]
        metadata = {key: value for key, value in data.items() if key != "vehicles"}
        return cls(vehicles, metadata=metadata)

    def __hash__(self) -> int:
        return hash(self.state_key())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Board):
            return NotImplemented
        return self.state_key() == other.state_key()

    def __repr__(self) -> str:
        return f"Board({self.state_key()!r})"
