"""
Neural embedding network for static hand gestures (Step 1).

    input  : 89-dim pose vector (canonical coords, joint angles,
             fingertip distances, abduction) — standardised
    output : 64-dim L2-normalised embedding

    Dense(256) ─ BN ─ ReLU ─ Dropout(0.1)
    Dense(256) ─ BN ─ ReLU ─ Dropout(0.1)
    Dense(128) ─ ReLU
    Dense(64)  ─ UnitNormalization          → embedding

Trained with a CosFace margin head on synthetic pose classes so that the
cosine distance between embeddings measures *pose similarity*,
independent of hand size, viewpoint and tracking noise.
"""

import keras
from keras import layers

from airauth.static_gesture.features import POSE_FEATURE_DIM

EMBEDDING_DIM = 64


def build_static_embedding_model(input_dim=POSE_FEATURE_DIM, embedding_dim=EMBEDDING_DIM):

    inputs = keras.Input(shape=(input_dim,), name="pose_vector")

    x = inputs
    for units in (256, 256):
        x = layers.Dense(units, use_bias=False)(x)
        x = layers.BatchNormalization()(x)
        x = layers.ReLU()(x)
        x = layers.Dropout(0.1)(x)

    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dense(embedding_dim)(x)
    outputs = layers.UnitNormalization(name="embedding")(x)

    return keras.Model(inputs, outputs, name="static_gesture_embedding")


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# embedding_model.py defines the Step-1 neural architecture: a 3-hidden-layer
# MLP with batch-norm and dropout that maps the 89 pose-invariant key-point
# features to a 64-dimensional unit-length embedding.  It only uses built-in
# Keras layers so the saved .keras file loads without custom objects.
# Training (pipelines/train_static_gesture_model.py) attaches a CosFace head;
# inference (airauth/common/model_registry.py) uses this network alone.
# =============================================================================
