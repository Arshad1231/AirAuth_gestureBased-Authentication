"""
Helpers shared by every training / evaluation pipeline.
"""

import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

from airauth.common import metrics  # noqa: E402


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("airauth.pipeline")


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    try:
        import keras
        keras.utils.set_random_seed(seed)
    except ImportError:  # pragma: no cover
        pass


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return path


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def model_version(prefix):
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.seconds = time.perf_counter() - self.start


# ---------------------------------------------------------------------------
# TRAINING
# ---------------------------------------------------------------------------

def standardisation_stats(inputs):
    """Per-feature (or per-channel for sequences) mean and std."""

    axes = tuple(range(inputs.ndim - 1))
    mean = inputs.mean(axis=axes)
    std = inputs.std(axis=axes) + 1e-6
    return mean.astype(np.float32), std.astype(np.float32)


def train_embedding_model(embedding_model, inputs, labels, epochs, batch_size,
                          learning_rate=1e-3, margin=0.35, scale=30.0, log=None):
    """
    Train an embedding network with a temporary CosFace head.
    Returns (mean, std, history_dict).  The embedding model is trained
    in place.
    """

    import keras

    from airauth.common.margin_head import build_training_model

    mean, std = standardisation_stats(inputs)
    standardised = ((inputs - mean) / std).astype(np.float32)

    num_classes = int(labels.max()) + 1
    trainer = build_training_model(embedding_model, num_classes, scale=scale, margin=margin)
    trainer.optimizer.learning_rate = learning_rate

    callbacks = [
        keras.callbacks.ReduceLROnPlateau(monitor="loss", factor=0.5, patience=3, min_lr=1e-5),
    ]

    history = trainer.fit(
        [standardised, labels.reshape(-1, 1)],
        labels,
        epochs=epochs,
        batch_size=batch_size,
        shuffle=True,
        callbacks=callbacks,
        verbose=2,
    )

    return mean, std, {key: [float(v) for v in values] for key, values in history.history.items()}


def embed(embedding_model, inputs, mean, std, batch_size=512):
    standardised = ((inputs - mean) / std).astype(np.float32)
    return np.asarray(embedding_model.predict(standardised, batch_size=batch_size, verbose=0))


def embedding_pair_metrics(embeddings, labels, max_impostor_pairs=50000, seed=0):
    """
    Verification quality of an embedding space: cosine distance of all
    same-class pairs vs. a random sample of different-class pairs.
    """

    rng = np.random.default_rng(seed)
    labels = np.asarray(labels)

    genuine = []
    for label in np.unique(labels):
        index = np.where(labels == label)[0]
        block = embeddings[index]
        sims = block @ block.T
        upper = np.triu_indices(len(index), k=1)
        genuine.extend(1.0 - sims[upper])

    count = len(labels)
    a = rng.integers(0, count, max_impostor_pairs)
    b = rng.integers(0, count, max_impostor_pairs)
    keep = labels[a] != labels[b]
    impostor = 1.0 - np.sum(embeddings[a[keep]] * embeddings[b[keep]], axis=1)

    return metrics.summarize(np.array(genuine), impostor)


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# pipeline_utils.py contains the plumbing shared by all pipelines: logging,
# reproducible seeding (Python/NumPy/Keras), JSON writing, model version
# strings, a timer, per-feature standardisation statistics, the generic
# CosFace training loop (train_embedding_model), batched embedding and
# embedding_pair_metrics(), which measures EER / ROC-AUC of an embedding
# space on genuine (same-class) vs impostor (different-class) pairs.
# =============================================================================
