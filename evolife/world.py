from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .config import (
    MINERALS_BAND_TOP_FRAC,
    MINERALS_BASE_PER_CELL,
    MINERALS_DEPTH_MULT,
    ORGANIC_ENERGY_PER_UNIT,
)


EMPTY = 0
WALL = 1
BOT = 2
ORGANIC = 3


@dataclass
class Cell:
    kind: int = EMPTY
    entity_id: Optional[int] = None  # refers to bot index in scheduler
    organic: float = 0.0
    minerals: float = 0.0


class World:
    def __init__(self, width: int, height: int) -> None:
        assert width >= 8 and height >= 8
        self.width = width
        self.height = height

        self.grid: List[List[Cell]] = [
            [Cell() for _ in range(width)] for _ in range(height)
        ]

        # Initialize walls on top/bottom
        for x in range(width):
            self.grid[0][x].kind = WALL
            self.grid[0][x].entity_id = None
            self.grid[height - 1][x].kind = WALL
            self.grid[height - 1][x].entity_id = None

        # Initialize minerals in lower half
        minerals_top = int(height * MINERALS_BAND_TOP_FRAC)
        for y in range(minerals_top, height - 1):  # exclude bottom wall
            depth_factor = (y - minerals_top + 1)
            base = MINERALS_BASE_PER_CELL + depth_factor * MINERALS_DEPTH_MULT * MINERALS_BASE_PER_CELL
            for x in range(width):
                self.grid[y][x].minerals = base

    def wrap_x(self, x: int) -> int:
        if x < 0:
            return x % self.width
        if x >= self.width:
            return x % self.width
        return x

    def clamp_y(self, y: int) -> int:
        if y < 0:
            return 0
        if y >= self.height:
            return self.height - 1
        return y

    def in_bounds_playable(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 < y < self.height - 1

    def get(self, x: int, y: int) -> Cell:
        return self.grid[y][x]

    def set_bot(self, x: int, y: int, entity_id: Optional[int]) -> None:
        cell = self.get(x, y)
        if entity_id is None:
            if cell.kind == BOT:
                cell.kind = EMPTY
                cell.entity_id = None
        else:
            cell.kind = BOT
            cell.entity_id = entity_id

    def set_empty(self, x: int, y: int) -> None:
        cell = self.get(x, y)
        cell.kind = EMPTY
        cell.entity_id = None

    def add_organic(self, x: int, y: int, energy: float) -> None:
        cell = self.get(x, y)
        cell.kind = ORGANIC
        cell.organic += max(0.0, energy)

    def tick_physics(self) -> None:
        # Sink organic down until blocked
        for y in range(self.height - 2, 0, -1):  # from bottom-1 up to 1
            for x in range(self.width):
                cell = self.grid[y][x]
                if cell.kind == ORGANIC and cell.organic > 0:
                    below = self.grid[y + 1][x]
                    if below.kind == EMPTY:
                        below.kind = ORGANIC
                        below.organic += cell.organic
                        cell.kind = EMPTY
                        cell.organic = 0.0

    def photo_energy_at(self, y: int) -> int:
        # Higher rows (closer to top wall) yield more energy. Top wall is y=0; first playable row y=1 has highest.
        if y >= self.height // 2:
            return 0
        # Linear falloff from top playable to midline
        top_playable = 1
        depth = max(0, y - top_playable)
        span = max(1, self.height // 2 - top_playable)
        level = max(0.0, 1.0 - depth / span)
        # Map to integer energy units
        from .config import PHOTO_BASE_TOP

        return max(0, int(PHOTO_BASE_TOP * level))

