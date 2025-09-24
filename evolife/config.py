from __future__ import annotations

# World
GENOME_SIZE = 64
VM_MAX_NONTERMINATING = 15

# Energy
INITIAL_ENERGY = 20
BASE_METABOLISM = 1
MOVE_COST = 1
SHARE_COST = 1
EAT_COST = 0
PHOTO_BASE_TOP = 8  # energy at the topmost water row beneath wall
PHOTO_MIN_DEPTH = 1  # first playable row index for sunlight (beneath top wall)

MINERALS_BAND_TOP_FRAC = 0.5  # lower half has minerals
MINERALS_BASE_PER_CELL = 20.0
MINERALS_DEPTH_MULT = 0.5  # deeper -> more
MINE_MAX_PER_ACTION = 6.0
MINE_EFFICIENCY = 1.0  # energy gain per mineral unit consumed

ORGANIC_ENERGY_PER_UNIT = 1.0
ORGANIC_DECAY = 0.0  # keep simple: no decay, only sinking

# Reproduction
REPRODUCTION_THRESHOLD = 40
MAX_ENERGY = 80
REPRODUCTION_COST = 20  # taken from parent when a child is created
MUTATION_RATE = 0.25  # 1 in 4 chance to mutate one byte

# Rendering
TICKS_PER_RENDER = 1

# Opcodes
OP_PHOTOSYNTHESIS = 23
OP_TURN_ABS = 25
OP_STEP = 26
OP_LOOK = 30
OP_EAT = 31
OP_SHARE = 32
OP_ENERGY_COMPARE = 33
OP_MINE = 34
OP_TURN_REL = 35
OP_SNIFF_LIGHT = 36

# Directions: 0..7 (N, NE, E, SE, S, SW, W, NW)
DIRECTION_DELTAS = (
    (0, -1),  # N
    (1, -1),  # NE
    (1, 0),   # E
    (1, 1),   # SE
    (0, 1),   # S
    (-1, 1),  # SW
    (-1, 0),  # W
    (-1, -1), # NW
)

