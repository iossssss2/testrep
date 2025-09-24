from __future__ import annotations

import shutil
from typing import List

from .sim import Simulation
from .world import World, EMPTY, WALL, BOT, ORGANIC


PALETTE = {
    EMPTY: " ",
    WALL: "#",
    BOT: "B",
    ORGANIC: ",",
}


def render(world: World, sim: Simulation, step: int) -> None:
    width = world.width
    height = world.height
    # Prepare string lines
    lines: List[str] = []
    lines.append(f"step={step} bots={len(sim.bots)}")
    for y in range(height):
        row_chars = []
        for x in range(width):
            cell = world.grid[y][x]
            ch = PALETTE.get(cell.kind, "?")
            row_chars.append(ch)
        lines.append("".join(row_chars))
    # Clear screen and print
    print("\x1b[H\x1b[2J", end="")
    print("\n".join(lines))

