"""
Lazy loader for the trained Keras embedding models.

TensorFlow is imported only when a model file actually exists, so the
service (and the unit tests) still run with the template matchers alone
when no model has been trained yet or TensorFlow is unavailable.
"""

import json
import logging
import os
import threading

import numpy as np

from airauth import config

logger = logging.getLogger(__name__)

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")


class EmbeddingModelHandle:
    """A loaded embedding model plus its input-standardisation metadata."""

    def __init__(self, name, model_path, meta_path):
        self.name = name
        self.model_path = model_path
        self.meta_path = meta_path
        self.model = None
        self._infer = None
        self.meta = {}
        self.load_error = None
        self._lock = threading.Lock()
        self._attempted = False

    # ------------------------------------------------------------------

    def _load(self):

        if self._attempted:
            return

        with self._lock:

            if self._attempted:
                return

            self._attempted = True

            if not config.ENABLE_NEURAL_MODELS:
                self.load_error = "neural models disabled by configuration"
                return

            if not self.model_path.exists():
                self.load_error = f"model file not found: {self.model_path.name}"
                return

            try:
                import keras  # noqa: WPS433 (deferred heavy import)

                self.model = keras.models.load_model(self.model_path, compile=False)
                self._infer = self._compile_inference(self.model)

                with open(self.meta_path, "r", encoding="utf-8") as handle:
                    self.meta = json.load(handle)

                logger.info("Loaded %s model (%s)", self.name, self.version)

            except Exception as error:  # pragma: no cover - environment specific
                self.model = None
                self.load_error = f"failed to load model: {error}"
                logger.warning("Could not load %s model: %s", self.name, error)

    @staticmethod
    def _compile_inference(model):
        """
        Eager Keras calls of recurrent layers are very slow (~2 s for the
        BiGRU).  A tf.function with a batch-agnostic input signature is
        traced once and then runs as a graph (tens of milliseconds).
        """

        try:
            import tensorflow as tf

            spec = tf.TensorSpec(shape=(None,) + tuple(model.input_shape[1:]), dtype=tf.float32)
            return tf.function(lambda x: model(x, training=False), input_signature=[spec])
        except Exception:  # pragma: no cover - non-TF backend
            return lambda x: model(x, training=False)

    # ------------------------------------------------------------------

    @property
    def available(self):
        self._load()
        return self.model is not None

    @property
    def version(self):
        return self.meta.get("model_version", "unavailable")

    def status(self):
        self._load()
        return {
            "available": self.model is not None,
            "version": self.version if self.model is not None else None,
            "error": self.load_error,
        }

    def embed(self, inputs):
        """
        inputs: array shaped like the model input *without* standardisation.
        Returns L2-normalised embeddings, or None if no model is loaded.
        """

        self._load()

        if self.model is None:
            return None

        inputs = np.asarray(inputs, dtype=np.float32)

        mean = np.asarray(self.meta["input_mean"], dtype=np.float32)
        std = np.asarray(self.meta["input_std"], dtype=np.float32)

        standardised = (inputs - mean) / std

        embeddings = self._infer(standardised)

        return np.asarray(embeddings, dtype=np.float64)

    def warm_up(self):
        """Trace the inference graph once (≈ seconds) so the first login is fast."""

        self._load()

        if self.model is not None:
            shape = (1,) + tuple(self.model.input_shape[1:])
            self.embed(np.zeros(shape, dtype=np.float32))

    def reset(self):
        """Forget the cached model (used after retraining)."""

        with self._lock:
            self.model = None
            self.meta = {}
            self.load_error = None
            self._attempted = False


static_gesture_model = EmbeddingModelHandle(
    "static_gesture",
    config.STATIC_MODEL_PATH,
    config.STATIC_MODEL_META_PATH,
)

dynamic_signature_model = EmbeddingModelHandle(
    "dynamic_signature",
    config.DYNAMIC_MODEL_PATH,
    config.DYNAMIC_MODEL_META_PATH,
)


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# model_registry.py owns the two neural embedding models used at inference:
#   static_gesture_model     -> models/static_gesture_embedding.keras
#   dynamic_signature_model  -> models/dynamic_signature_embedding.keras
# Each EmbeddingModelHandle loads its .keras file and JSON metadata on first
# use (thread-safe), compiles a graph-mode inference function (eager BiGRU
# calls are ~50x slower), applies the stored input mean/std standardisation
# and returns L2-normalised embeddings.  If the model is missing, disabled or
# fails to load, embed() returns None and the verifiers fall back to their
# non-neural components instead of crashing.
# =============================================================================
