from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .config import (
    BASE_METABOLISM,
    DIRECTION_DELTAS,
    EAT_COST,
    GENOME_SIZE,
    MAX_ENERGY,
    MINE_EFFICIENCY,
    MINE_MAX_PER_ACTION,
    MOVE_COST,
    MUTATION_RATE,
    OP_ENERGY_COMPARE,
    OP_EAT,
    OP_LOOK,
    OP_MINE,
    OP_PHOTOSYNTHESIS,
    OP_SHARE,
    OP_STEP,
    OP_TURN_ABS,
    OP_TURN_REL,
    REPRODUCTION_COST,
    REPRODUCTION_THRESHOLD,
    SHARE_COST,
    VM_MAX_NONTERMINATING,
)
from .world import World, EMPTY, WALL, BOT, ORGANIC


def mod64(value: int) -> int:
    return value & 63


@dataclass
class Bot:
    genome: List[int]
    x: int
    y: int
    energy: int
    dir: int = 0  # 0..7
    ip: int = 0
    id: Optional[int] = None  # assigned by scheduler

    # Cached state updated each turn
    executed_nonterm: int = 0

    def clone_with_mutation(self, child_id: int, world: World) -> Optional["Bot"]:
        if self.energy < REPRODUCTION_COST:
            return None
        # Find adjacent empty spot for child, starting clockwise from current dir
        for offset in range(8):
            d = (self.dir + offset) & 7
            dx, dy = DIRECTION_DELTAS[d]
            nx = world.wrap_x(self.x + dx)
            ny = world.clamp_y(self.y + dy)
            if not world.in_bounds_playable(nx, ny):
                continue
            cell = world.get(nx, ny)
            if cell.kind == EMPTY:
                break
        else:
            # No space
            return None

        child_genome = list(self.genome)
        if random.random() < MUTATION_RATE:
            idx = random.randrange(GENOME_SIZE)
            child_genome[idx] = random.randrange(64)

        child = Bot(
            genome=child_genome,
            x=nx,
            y=ny,
            energy=REPRODUCTION_COST,
            dir=self.dir,
            ip=0,
            id=child_id,
        )
        self.energy -= REPRODUCTION_COST
        return child

    def same_species(self, other: "Bot") -> bool:
        # same if genomes differ by at most 1 byte
        diff = 0
        for a, b in zip(self.genome, other.genome):
            if a != b:
                diff += 1
                if diff > 1:
                    return False
        return True

    def try_reproduce(self, request_child_id: int, world: World) -> Optional["Bot"]:
        if self.energy >= REPRODUCTION_THRESHOLD and self.energy <= MAX_ENERGY - REPRODUCTION_COST:
            return self.clone_with_mutation(request_child_id, world)
        return None

    def run_turn(self, world: World) -> None:
        self.executed_nonterm = 0

        while self.executed_nonterm < VM_MAX_NONTERMINATING:
            opcode = self.genome[mod64(self.ip)]

            if opcode == OP_PHOTOSYNTHESIS:
                self.energy += world.photo_energy_at(self.y)
                self.ip = mod64(self.ip + 1)
                break

            elif opcode == OP_TURN_ABS:
                param = self.genome[mod64(self.ip + 1)]
                self.dir = param % 8
                self.ip = mod64(self.ip + 2)
                self.executed_nonterm += 1
                continue

            elif opcode == OP_TURN_REL:
                param = self.genome[mod64(self.ip + 1)]
                self.dir = (self.dir + (param % 8)) & 7
                self.ip = mod64(self.ip + 2)
                self.executed_nonterm += 1
                continue

            elif opcode == OP_LOOK:
                param = self.genome[mod64(self.ip + 1)]
                d = (self.dir + (param % 8)) & 7
                dx, dy = DIRECTION_DELTAS[d]
                nx = world.wrap_x(self.x + dx)
                ny = world.clamp_y(self.y + dy)
                cell = world.get(nx, ny)
                # Branching based on target content
                if cell.kind == EMPTY:
                    branch = self.genome[mod64(self.ip + 2)]
                elif cell.kind == BOT:
                    branch = self.genome[mod64(self.ip + 3)]
                elif cell.kind == ORGANIC:
                    branch = self.genome[mod64(self.ip + 4)]
                else:  # WALL
                    branch = self.genome[mod64(self.ip + 5)]
                self.ip = mod64(self.ip + branch)
                self.executed_nonterm += 1
                continue

            elif opcode == OP_STEP:
                dx, dy = DIRECTION_DELTAS[self.dir]
                nx = world.wrap_x(self.x + dx)
                ny = world.clamp_y(self.y + dy)
                target = world.get(nx, ny)
                if target.kind == EMPTY:
                    world.set_empty(self.x, self.y)
                    self.x, self.y = nx, ny
                    world.set_bot(self.x, self.y, self.id)
                    branch = self.genome[mod64(self.ip + 1)]
                elif target.kind == BOT:
                    branch = self.genome[mod64(self.ip + 2)]
                elif target.kind == ORGANIC:
                    branch = self.genome[mod64(self.ip + 3)]
                else:  # WALL
                    branch = self.genome[mod64(self.ip + 4)]
                # movement attempt costs energy regardless
                self.energy -= MOVE_COST
                self.ip = mod64(self.ip + branch)
                break

            elif opcode == OP_EAT:
                dx, dy = DIRECTION_DELTAS[self.dir]
                nx = world.wrap_x(self.x + dx)
                ny = world.clamp_y(self.y + dy)
                target = world.get(nx, ny)
                if target.kind == BOT and target.entity_id is not None:
                    from .sim import Simulation  # avoid cycle

                    prey = Simulation.lookup_bot(target.entity_id)
                    if prey is not None and prey.energy >= 0:
                        self.energy += max(0, prey.energy)
                        prey.energy = -1
                        Simulation.mark_eaten(prey.id)
                    branch = self.genome[mod64(self.ip + 2)]
                elif target.kind == ORGANIC and target.organic > 0:
                    eaten = min(target.organic, 8.0)
                    target.organic -= eaten
                    self.energy += int(eaten)
                    if target.organic <= 0:
                        world.set_empty(nx, ny)
                    branch = self.genome[mod64(self.ip + 3)]
                elif target.kind == EMPTY:
                    branch = self.genome[mod64(self.ip + 1)]
                else:  # WALL
                    branch = self.genome[mod64(self.ip + 4)]
                self.energy -= EAT_COST
                self.ip = mod64(self.ip + branch)
                break

            elif opcode == OP_SHARE:
                # Share energy with the bot ahead if same species
                dx, dy = DIRECTION_DELTAS[self.dir]
                nx = world.wrap_x(self.x + dx)
                ny = world.clamp_y(self.y + dy)
                cell = world.get(nx, ny)
                if cell.kind == BOT and cell.entity_id is not None:
                    from .sim import Simulation

                    other = Simulation.lookup_bot(cell.entity_id)
                    if other is not None and self.same_species(other) and self.energy > 1:
                        give = max(1, self.energy // 4)
                        give = min(give, self.energy - 1)
                        self.energy -= give
                        other.energy = min(MAX_ENERGY, other.energy + give)
                    branch = self.genome[mod64(self.ip + 2)]
                elif cell.kind == ORGANIC:
                    branch = self.genome[mod64(self.ip + 3)]
                elif cell.kind == EMPTY:
                    branch = self.genome[mod64(self.ip + 1)]
                else:  # WALL
                    branch = self.genome[mod64(self.ip + 4)]
                self.energy -= SHARE_COST
                self.ip = mod64(self.ip + branch)
                break

            elif opcode == OP_ENERGY_COMPARE:
                param = self.genome[mod64(self.ip + 1)]
                threshold = param * 15
                ge_branch = self.genome[mod64(self.ip + 2)]
                lt_branch = self.genome[mod64(self.ip + 3)]
                if self.energy >= threshold:
                    self.ip = mod64(self.ip + ge_branch)
                else:
                    self.ip = mod64(self.ip + lt_branch)
                self.executed_nonterm += 1
                continue

            elif opcode == OP_MINE:
                # Harvest minerals from current cell
                cell = world.get(self.x, self.y)
                if cell.minerals > 0:
                    mined = min(MINE_MAX_PER_ACTION, cell.minerals)
                    cell.minerals -= mined
                    self.energy += int(mined * MINE_EFFICIENCY)
                self.ip = mod64(self.ip + 1)
                break

            else:
                # Unconditional relative jump by opcode value
                self.ip = mod64(self.ip + opcode)
                self.executed_nonterm += 1
                continue

        # Basal metabolism cost after turn
        self.energy -= BASE_METABOLISM

