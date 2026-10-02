"""
Loaders that turn on-disk datasets into the same JSON sample format the
API receives from the browser, so training, evaluation and live
verification all share one preprocessing path.
"""

import csv
import json
from pathlib import Path

from airauth import config

# The original desktop collector that recorded the research dataset
# requested 1280x720 camera frames.
RESEARCH_FRAME_SIZE = (1280, 720)


def load_research_signatures(root=None):
    """
    data/research_signatures/<USER>/<SESSION>/signature_XXX.csv
    (columns: timestamp, x, y, z)

    Returns a list of records:
        {"user_id", "session_id", "sample_id", "sample": {points, width, height}}
    """

    root = Path(root or config.RESEARCH_SIGNATURE_DATASET_DIR)
    records = []

    if not root.exists():
        return records

    for csv_path in sorted(root.glob("*/*/signature_*.csv")):

        with open(csv_path, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        points = [
            [float(row["timestamp"]), float(row["x"]), float(row["y"]), float(row["z"])]
            for row in rows
        ]

        records.append(
            {
                "user_id": csv_path.parent.parent.name,
                "session_id": csv_path.parent.name,
                "sample_id": csv_path.stem,
                "sample": {
                    "points": points,
                    "width": RESEARCH_FRAME_SIZE[0],
                    "height": RESEARCH_FRAME_SIZE[1],
                },
            }
        )

    return records


def load_collected_samples(kind, root=None):
    """
    Samples exported from MongoDB by server/scripts/exportBiometricSamples.js

        data/collected/static/*.jsonl    kind="static"
        data/collected/dynamic/*.jsonl   kind="dynamic"

    Each line: {"user_id", "session_id", "sample_id", "purpose", "sample"}
    """

    root = Path(root or config.COLLECTED_DATA_DIR) / kind
    records = []

    if not root.exists():
        return records

    for path in sorted(root.glob("*.jsonl")):
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

    return records


def group_by_user(records):
    users = {}
    for record in records:
        users.setdefault(record["user_id"], []).append(record)
    return users


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# dataset_loader.py reads the two on-disk data sources into API-shaped
# samples:
#   load_research_signatures()  the research dataset in data/research_signatures
#                             (CSV per signature, user/session folders,
#                             recorded with a 1280x720 camera)
#   load_collected_samples()  JSON-lines exported from MongoDB after users
#                             register/log in through the web app
#   group_by_user()           convenience grouping for evaluation protocols
# Because the output matches the live API format, every pipeline reuses the
# exact preprocessing that runs in production.
# =============================================================================
