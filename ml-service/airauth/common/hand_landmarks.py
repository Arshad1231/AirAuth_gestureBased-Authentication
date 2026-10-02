"""
MediaPipe Hands landmark topology shared by the static-gesture feature
extractor and the synthetic hand generator.

    0  WRIST
    1  THUMB_CMC   2  THUMB_MCP   3  THUMB_IP    4  THUMB_TIP
    5  INDEX_MCP   6  INDEX_PIP   7  INDEX_DIP   8  INDEX_TIP
    9  MIDDLE_MCP 10  MIDDLE_PIP 11  MIDDLE_DIP 12  MIDDLE_TIP
   13  RING_MCP   14  RING_PIP   15  RING_DIP   16  RING_TIP
   17  PINKY_MCP  18  PINKY_PIP  19  PINKY_DIP  20  PINKY_TIP
"""

NUM_LANDMARKS = 21

WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_TIP = 8
MIDDLE_MCP = 9
RING_MCP = 13
PINKY_MCP = 17

# Each finger as a chain starting at the wrist.
FINGER_CHAINS = {
    "thumb": [0, 1, 2, 3, 4],
    "index": [0, 5, 6, 7, 8],
    "middle": [0, 9, 10, 11, 12],
    "ring": [0, 13, 14, 15, 16],
    "pinky": [0, 17, 18, 19, 20],
}

FINGER_NAMES = list(FINGER_CHAINS.keys())

FINGERTIPS = [4, 8, 12, 16, 20]

PALM_BASE_POINTS = [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]

# All 20 bones (parent, child) — used for hand-geometry ratios.
BONES = [
    (chain[i], chain[i + 1])
    for chain in FINGER_CHAINS.values()
    for i in range(len(chain) - 1)
]

# Joint triplets (a, b, c): flexion angle measured at b.
JOINT_TRIPLETS = [
    (chain[i - 1], chain[i], chain[i + 1])
    for chain in FINGER_CHAINS.values()
    for i in range(1, len(chain) - 1)
]

# Adjacent finger pairs whose spread (abduction) is measured.
ABDUCTION_PAIRS = [
    ("thumb", "index"),
    ("index", "middle"),
    ("middle", "ring"),
    ("ring", "pinky"),
]

HAND_CONNECTIONS = BONES + [(5, 9), (9, 13), (13, 17)]


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# hand_landmarks.py defines the 21-point MediaPipe hand skeleton as plain
# Python constants: landmark indices, the five finger chains, fingertip ids,
# the 20 bones, the 15 joint triplets used for flexion angles and the finger
# pairs used for abduction angles.  Both the feature extractor and the
# synthetic hand generator import these so they always agree on topology.
# =============================================================================
