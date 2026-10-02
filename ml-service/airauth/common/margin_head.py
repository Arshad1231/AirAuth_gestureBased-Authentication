"""
CosFace (Large-Margin Cosine) classification head used only while
training the embedding networks.

Training as a margin-based classifier and then throwing the head away is
a standard way to learn a *metric* embedding: the L2-normalised
embedding is pushed to have a cosine margin between classes, so at
inference we can verify unseen users / gestures by cosine distance.

    logits = s * (cos(θ_j) - m * [j == y])
"""

import keras
from keras import ops


@keras.saving.register_keras_serializable(package="airauth")
class CosFaceHead(keras.layers.Layer):

    def __init__(self, num_classes, scale=30.0, margin=0.35, **kwargs):
        super().__init__(**kwargs)
        self.num_classes = int(num_classes)
        self.scale = float(scale)
        self.margin = float(margin)

    def build(self, input_shape):
        embedding_shape = input_shape[0]
        self.class_centres = self.add_weight(
            name="class_centres",
            shape=(embedding_shape[-1], self.num_classes),
            initializer="glorot_uniform",
            trainable=True,
        )

    def call(self, inputs):
        embeddings, labels = inputs

        centres = self.class_centres / (
            ops.sqrt(ops.sum(ops.square(self.class_centres), axis=0, keepdims=True)) + 1e-9
        )
        cosine = ops.matmul(embeddings, centres)

        one_hot = ops.one_hot(ops.cast(ops.reshape(labels, (-1,)), "int32"), self.num_classes)

        return self.scale * (cosine - self.margin * one_hot)

    def get_config(self):
        config = super().get_config()
        config.update(
            {"num_classes": self.num_classes, "scale": self.scale, "margin": self.margin}
        )
        return config


def build_training_model(embedding_model, num_classes, scale=30.0, margin=0.35):
    """Wrap an embedding model with a CosFace head: inputs = [x, labels]."""

    labels = keras.Input(shape=(1,), dtype="int32", name="labels")
    embeddings = embedding_model.output
    logits = CosFaceHead(num_classes, scale, margin, name="cosface")([embeddings, labels])

    model = keras.Model([embedding_model.input, labels], logits, name="cosface_trainer")
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["sparse_categorical_accuracy"],
    )

    return model


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# margin_head.py provides CosFaceHead, a Keras layer that normalises learnable
# class centres and outputs scaled cosine logits with an additive margin on
# the true class, and build_training_model(), which bolts this head onto any
# embedding network and compiles it with cross-entropy.  Both training
# pipelines use it; only the bare embedding network is saved for inference,
# so the head (and its class list) never reaches production.
# =============================================================================
