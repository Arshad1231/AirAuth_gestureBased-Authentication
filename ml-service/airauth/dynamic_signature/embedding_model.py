"""
Neural embedding network for in-air signatures (Step 2).

    input  : (128 timesteps, 9 channels)  standardised sequence features
             x, y, vx, vy, speed, sin θ, cos θ, curvature, accel
    output : 64-dim L2-normalised embedding

    Conv1D(64, k=5) ─ BN ─ ReLU          local stroke shape / velocity
    Conv1D(64, k=5) ─ BN ─ ReLU
    Bidirectional GRU(64, sequences)     long-range order and rhythm
    Attention pooling                    learns which parts of the
        Dense(1) ─ Softmax(time)         signature are most identifying
        weighted sum over time
    Dense(128) ─ ReLU ─ Dropout(0.2)
    Dense(64)  ─ UnitNormalization       → embedding

Trained with a CosFace margin head on synthetic writers + skilled forgers
(pipelines/train_dynamic_signature_model.py).  Verification compares a
probe embedding with the centroid of the user's enrollment embeddings.
"""

import keras
from keras import layers

from airauth import config
from airauth.dynamic_signature.features import SEQUENCE_CHANNELS

EMBEDDING_DIM = 64


def build_dynamic_embedding_model(
    sequence_length=config.SEQUENCE_LENGTH,
    channels=len(SEQUENCE_CHANNELS),
    embedding_dim=EMBEDDING_DIM,
):

    inputs = keras.Input(shape=(sequence_length, channels), name="signature_sequence")

    x = inputs
    for _ in range(2):
        x = layers.Conv1D(64, 5, padding="same", use_bias=False)(x)
        x = layers.BatchNormalization()(x)
        x = layers.ReLU()(x)

    hidden = layers.Bidirectional(layers.GRU(64, return_sequences=True), name="bigru")(x)

    scores = layers.Dense(1, name="attention_score")(hidden)
    weights = layers.Softmax(axis=1, name="attention_weights")(scores)
    pooled = layers.Dot(axes=1, name="attention_pool")([weights, hidden])
    pooled = layers.Flatten()(pooled)

    x = layers.Dense(128, activation="relu")(pooled)
    x = layers.Dropout(0.2)(x)
    x = layers.Dense(embedding_dim)(x)
    outputs = layers.UnitNormalization(name="embedding")(x)

    return keras.Model(inputs, outputs, name="dynamic_signature_embedding")


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# embedding_model.py defines the Step-2 neural architecture: two 1-D
# convolution blocks for local stroke patterns, a bidirectional GRU for the
# temporal order and rhythm of the signature, attention pooling that weights
# the most identifying moments, and a dense projection to a 64-d unit-length
# embedding.  Only built-in Keras layers are used, so the saved .keras file
# loads without custom objects at inference time.
# =============================================================================
