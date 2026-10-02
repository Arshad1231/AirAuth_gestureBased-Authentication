"""
PIPELINE 1 â€” Train the static-gesture embedding network (Step 1).

    synthetic pose classes â”€â”€â”
    (optional) real captures â”¤â”€> preprocessing â”€> key-point features
                             â”‚     â”€> pose vector (89) â”€> MLP + CosFace
                             â””â”€> held-out pose classes â”€> EER report
    outputs:
        models/static_gesture_embedding.keras
        models/static_gesture_embedding.json   (version, input mean/std, metrics)

Usage (from ml-service/):
    python -m pipelines.train_static_gesture_model
    python -m pipelines.train_static_gesture_model --epochs 30 --collected
"""

import argparse

import numpy as np

from airauth import config
from airauth.common.errors import BiometricInputError
from airauth.common.model_registry import static_gesture_model
from airauth.data.dataset_loader import group_by_user, load_collected_samples
from airauth.static_gesture import features
from airauth.static_gesture.embedding_model import build_static_embedding_model
from airauth.static_gesture.synthetic_hand import SyntheticHandGenerator, all_pose_combinations
from airauth.static_gesture.verifier import extract
from pipelines import pipeline_utils as utils


def split_pose_classes(seed, validation_fraction=0.2):
    combinations = all_pose_combinations()
    order = np.random.default_rng(seed).permutation(len(combinations))
    cut = int(len(combinations) * (1 - validation_fraction))
    return [combinations[i] for i in order[:cut]], [combinations[i] for i in order[cut:]]


def build_synthetic_set(generator, combinations, instances_per_class, flip_probability=0.5):
    """Pose vectors for every (class, instance); persons and viewpoints vary."""

    vectors, labels = [], []

    for label, combination in enumerate(combinations):

        pose = generator.make_pose_class(combination)

        for _ in range(instances_per_class):
            frames = generator.render(
                pose, generator.make_person(), generator.make_orientation(), n_frames=1
            )
            vector = features.pose_vector(features.extract_frame_features(frames[0]))
            vectors.append(vector)
            labels.append(label)

    vectors = np.asarray(vectors, dtype=np.float32)
    labels = np.asarray(labels, dtype=np.int32)

    flip = generator.rng.random(len(vectors)) < flip_probability
    vectors[flip] = features.flip_pose_chirality(vectors[flip])

    return vectors, labels


def build_collected_set(first_label, log):
    """Real gesture captures exported from the web app (one class per user)."""

    records = load_collected_samples("static")
    vectors, labels = [], []

    for offset, (user_id, user_records) in enumerate(sorted(group_by_user(records).items())):
        for record in user_records:
            try:
                vector, _, _ = extract(record["sample"])
            except BiometricInputError:
                continue
            vectors.append(features.pose_vector(vector))
            labels.append(first_label + offset)

    log.info("Collected real static samples: %d from %d users",
             len(vectors), len(set(labels)))

    if not vectors:
        return None, None

    return np.asarray(vectors, dtype=np.float32), np.asarray(labels, dtype=np.int32)


def main(argv=None):

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--instances", type=int, default=40, help="training samples per pose class")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--collected", action="store_true",
                        help="also train on real captures in data/collected/static")
    args = parser.parse_args(argv)

    log = utils.setup_logging()
    utils.set_seed(args.seed)

    train_classes, validation_classes = split_pose_classes(args.seed)
    log.info("Pose classes: %d train / %d held-out", len(train_classes), len(validation_classes))

    generator = SyntheticHandGenerator(args.seed)

    with utils.Timer() as timer:
        train_x, train_y = build_synthetic_set(generator, train_classes, args.instances)
        val_x, val_y = build_synthetic_set(generator, validation_classes, 10)
    log.info("Synthetic data: %d train / %d validation samples (%.1fs)",
             len(train_x), len(val_x), timer.seconds)

    if args.collected:
        real_x, real_y = build_collected_set(int(train_y.max()) + 1, log)
        if real_x is not None:
            train_x = np.concatenate([train_x, real_x])
            train_y = np.concatenate([train_y, real_y])

    model = build_static_embedding_model()
    model.summary(print_fn=log.info)

    with utils.Timer() as timer:
        mean, std, history = utils.train_embedding_model(
            model, train_x, train_y, epochs=args.epochs, batch_size=args.batch_size, log=log
        )
    log.info("Training finished in %.1fs", timer.seconds)

    val_embeddings = utils.embed(model, val_x, mean, std)
    validation = utils.embedding_pair_metrics(val_embeddings, val_y)
    log.info("Held-out pose classes  EER %.4f  ROC-AUC %.4f", validation["eer"], validation["roc_auc"])

    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model.save(config.STATIC_MODEL_PATH)

    version = utils.model_version("static")
    utils.write_json(
        config.STATIC_MODEL_META_PATH,
        {
            "model_version": version,
            "feature_version": config.STATIC_FEATURE_VERSION,
            "trained_at": utils.timestamp(),
            "input_dim": int(train_x.shape[1]),
            "input_mean": mean.tolist(),
            "input_std": std.tolist(),
            "train_samples": int(len(train_x)),
            "train_classes": int(train_y.max()) + 1,
            "epochs": args.epochs,
            "seed": args.seed,
            "used_collected_data": bool(args.collected),
            "validation_heldout_classes": validation,
            "final_loss": history["loss"][-1],
            "final_accuracy": history["sparse_categorical_accuracy"][-1],
        },
    )

    static_gesture_model.reset()
    log.info("Saved %s (%s)", config.STATIC_MODEL_PATH, version)


if __name__ == "__main__":
    main()


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# train_static_gesture_model.py is the training pipeline for the Step-1
# neural model.  It splits the 2,048 synthetic pose combinations into
# disjoint train / held-out sets, renders many persons and viewpoints per
# pose with SyntheticHandGenerator, extracts the 89-dim pose vectors (with
# mirror augmentation), optionally adds real captures exported from the web
# app (--collected), trains the MLP embedding with a CosFace head, measures
# EER on never-seen pose classes and saves the .keras model plus a JSON
# metadata file (version, standardisation stats, metrics) that the API
# loads at runtime.
# =============================================================================
