import argparse
import time
import random

from evolife.config import (
    GENOME_SIZE,
    INITIAL_ENERGY,
    TICKS_PER_RENDER,
)
from evolife.world import World
from evolife.sim import Simulation
from evolife.bot import Bot
from evolife import render as renderer


def create_initial_bot(world: World) -> Bot:
    genome = [23 for _ in range(GENOME_SIZE)]  # 23 = PHOTOSYNTHESIS
    # Place near the top, away from walls
    x = world.width // 2
    y = 2
    return Bot(genome=genome, x=x, y=y, energy=INITIAL_ENERGY)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Эволюция жизни — симуляция ботов")
    parser.add_argument("--width", type=int, default=80)
    parser.add_argument("--height", type=int, default=30)
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    world = World(width=args.width, height=args.height)
    sim = Simulation(world)

    first = create_initial_bot(world)
    sim.add_bot(first)

    last_render_time = 0.0
    target_frame = 1.0 / max(1, args.fps)

    for step in range(args.steps):
        sim.step()

        # Render at target FPS
        now = time.time()
        if now - last_render_time >= target_frame or step % TICKS_PER_RENDER == 0:
            renderer.render(world, sim, step)
            last_render_time = now

    # Final frame
    renderer.render(world, sim, args.steps)


if __name__ == "__main__":
    main()

