from __future__ import annotations

from typing import Dict, List, Optional

from .bot import Bot
from .world import World, EMPTY, BOT as BOT_KIND
from .config import MAX_ENERGY


class Simulation:
    # Global registry for quick lookups by id
    _registry: Dict[int, Bot] = {}
    _eaten_ids: set[int] = set()

    @classmethod
    def lookup_bot(cls, bot_id: int) -> Optional[Bot]:
        return cls._registry.get(bot_id)

    @classmethod
    def mark_eaten(cls, bot_id: int) -> None:
        cls._eaten_ids.add(bot_id)

    def __init__(self, world: World) -> None:
        self.world = world
        self.bots: List[Bot] = []
        self.next_id: int = 1
        self.cursor: int = 0  # index of the next bot to act

    def add_bot(self, bot: Bot) -> None:
        bot.id = self.next_id
        self.next_id += 1
        self.bots.insert(self.cursor, bot)  # new bot enters before parent is handled externally
        Simulation._registry[bot.id] = bot
        # place in world
        self.world.set_bot(bot.x, bot.y, bot.id)

    def step(self) -> None:
        if not self.bots:
            self.world.tick_physics()
            return

        bot = self.bots[self.cursor]
        if bot.energy < 0:
            self._remove_dead_at_cursor(convert_to_organic=True)
            self._advance_cursor()
            self.world.tick_physics()
            return

        bot.run_turn(self.world)

        # death checks
        if bot.energy < 0:
            self._remove_dead_at(self.cursor, convert_to_organic=True)
        else:
            # Reproduction
            # Reproduction rules
            if bot.energy >= MAX_ENERGY:
                # Must bud now; if cannot due to no space, die
                child = bot.clone_with_mutation(self.next_id, self.world)
                if child is None:
                    bot.energy = -1
                
            else:
                child = bot.try_reproduce(self.next_id, self.world)
            if child is not None:
                # Insert child before parent
                self.bots.insert(self.cursor, child)
                Simulation._registry[child.id] = child
                self.world.set_bot(child.x, child.y, child.id)
                self.next_id += 1

            # Cap energy
            if bot.energy > 0 and bot.energy > bot.__class__.__dict__.get("MAX_ENERGY", 0):
                pass  # handled by explicit MAX_ENERGY in logic; kept for clarity

        self._advance_cursor()
        self.world.tick_physics()

    def _advance_cursor(self) -> None:
        if not self.bots:
            self.cursor = 0
        else:
            self.cursor = (self.cursor + 1) % len(self.bots)

    def _remove_dead_at_cursor(self, convert_to_organic: bool) -> None:
        self._remove_dead_at(self.cursor, convert_to_organic)

    def _remove_dead_at(self, index: int, convert_to_organic: bool) -> None:
        bot = self.bots.pop(index)
        Simulation._registry.pop(bot.id or -1, None)
        cell = self.world.get(bot.x, bot.y)
        # If not eaten, convert to organic at position
        if bot.id in Simulation._eaten_ids:
            convert_to_organic = False
            Simulation._eaten_ids.discard(bot.id)
        if convert_to_organic and cell.kind == BOT_KIND and cell.entity_id == bot.id:
            self.world.add_organic(bot.x, bot.y, max(0, bot.energy))
        # Clear bot from cell (if still there)
        if cell.kind == BOT_KIND and cell.entity_id == bot.id:
            self.world.set_empty(bot.x, bot.y)
        if self.cursor >= len(self.bots):
            self.cursor = 0

