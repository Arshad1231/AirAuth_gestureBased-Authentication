"""
PIPELINE 2 â€” Train the dynamic air-signature embedding network (Step 2).

    synthetic writers + skilled forgers â”€â”€â”
    (optional) real signatures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤â”€> production preprocessing
                                          â”‚   â”€> sequence features (128 x 9)
                                          â”‚   â”€> Conv1D + BiGRU + attention
                                          â”‚      + CosFace head
                                          â””â”€> held-out writers / forgers
                                              + real research dataset
                                              â”€> EER report
    outputs:
        models/dynamic_signature_embedding.keras
        models/dynamic_signature_embedding.json

By default the real research dataset is NOT used for training â€” it is
kept clean for evaluation/calibration.  Pass --finetune-real once enough
users have been collected through the web app.

Usage (from ml-service/):
    python -m pipelines.train_dynamic_signature_model
    python -m pipelines.train_dynamic_signature_model --writers 600 --epochs 20
    python -m pipelines.train_dynamic_signature_model --finetune-real
"""

import argparse

import numpy as np

from airauth import config
from airauth.common.errors import BiometricInputError
from airauth.common.model_registry import dynamic_signature_model
from airauth.data.dataset_loader import group_by_user, load_collected_samples, load_research_signatures
from airauth.dynamic_signature.embedding_model import build_dynamic_embedding_model
from airauth.dynamic_signature.features import sequence_features
from airauth.dynamic_signature.preprocessing import preprocess_signature
from airauth.dynamic_signature.synthetic_signature import SyntheticSignatureGenerator
from pipelines import pipeline_utils as utils


def to_sequence(sample):
    return sequence_features(preprocess_signature(sample).xy)


def build_synthetic_set(generator, writers, renders, first_label=0):
    """
    Each writer contributes two classes: the writer and a skilled forger of
    that writer.  Returns sequences, labels and the forger->writer map.
    """

    sequences, labels, forger_of = [], [], {}
    label = first_label

    for _ in range(writers):

        writer = generator.make_writer()
        forger = generator.make_forger(writer)

        for identity, identity_label in ((writer, label), (forger, label + 1)):
            produced = 0
            while produced < renders:
                try:
                    sequences.append(to_sequence(generator.render(identity)))
                except BiometricInputError:
                    continue
                labels.append(identity_label)
                produced += 1

        forger_of[label + 1] = label
        label += 2

    return np.asarray(sequences, dtype=np.float32), np.asarray(labels, dtype=np.int32), forger_of


def build_real_set(first_label, log):
    """Research dataset + web-app exports, one class per user."""

    records = load_research_signatures() + load_collected_samples("dynamic")
    sequences, labels = [], []

    for offset, (_, user_records) in enumerate(sorted(group_by_user(records).items())):
        for record in user_records:
            try:
                sequences.append(to_sequence(record["sample"]))
            except BiometricInputError:
                continue
            labels.append(first_label + offset)

    log.info("Real signatures: %d from %d users", len(sequences), len(set(labels)))
    return np.asarray(sequences, dtype=np.float32), np.asarray(labels, dtype=np.int32)


def forgery_metrics(embeddings, labels, forger_of):
    """Genuine pairs vs. (writer, their skilled forger) pairs."""

    genuine, forgery = [], []

    for forger_label, writer_label in forger_of.items():
        writer = embeddings[labels == writer_label]
        forger = embeddings[labels == forger_label]
        sims = writer @ writer.T
        genuine.extend(1.0 - sims[np.triu_indices(len(writer), k=1)])
        forgery.extend((1.0 - writer @ forger.T).ravel())

    from airauth.common import metrics
    return metrics.summarize(np.array(genuine), np.array(forgery))


def main(argv=None):

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--writers", type=int, default=400, help="synthetic writers (each adds a forger)")
    parser.add_argument("--renders", type=int, default=12, help="samples per writer / forger")
    parser.add_argument("--epochs", type=int, default=18)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--finetune-real", action="store_true",
                        help="add the research dataset + web-app exports to training")
    args = parser.parse_args(argv)

    log = utils.setup_logging()
    utils.set_seed(args.seed)

    generator = SyntheticSignatureGenerator(args.seed)

    with utils.Timer() as timer:
        train_x, train_y, _ = build_synthetic_set(generator, args.writers, args.renders)
        val_x, val_y, val_forgers = build_synthetic_set(generator, 60, 6)
    log.info("Synthetic data: %d train / %d validation sequences (%.1fs)",
             len(train_x), len(val_x), timer.seconds)

    real_x, real_y = build_real_set(0, log)

    if args.finetune_real and len(real_x):
        train_x = np.concatenate([train_x, real_x])
        train_y = np.concatenate([train_y, real_y + int(train_y.max()) + 1])

    model = build_dynamic_embedding_model()
    model.summary(print_fn=log.info)

    with utils.Timer() as timer:
        mean, std, history = utils.train_embedding_model(
            model, train_x, train_y, epochs=args.epochs, batch_size=args.batch_size, log=log
        )
    log.info("Training finished in %.1fs", timer.seconds)

    val_embeddings = utils.embed(model, val_x, mean, std)
    validation = utils.embedding_pair_metrics(val_embeddings, val_y)
    forgeries = forgery_metrics(val_embeddings, val_y, val_forgers)
    log.info("Held-out writers   EER %.4f  ROC-AUC %.4f", validation["eer"], validation["roc_auc"])
    log.info("Skilled forgeries  EER %.4f  ROC-AUC %.4f", forgeries["eer"], forgeries["roc_auc"])

    real_metrics = None
    if len(real_x) and len(set(real_y.tolist())) > 1:
        real_metrics = utils.embedding_pair_metrics(utils.embed(model, real_x, mean, std), real_y)
        log.info("Research dataset   EER %.4f  ROC-AUC %.4f%s", real_metrics["eer"],
                 real_metrics["roc_auc"], "  (seen in training!)" if args.finetune_real else "")

    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model.save(config.DYNAMIC_MODEL_PATH)

    version = utils.model_version("dynamic")
    utils.write_json(
        config.DYNAMIC_MODEL_META_PATH,
        {
            "model_version": version,
            "feature_version": config.DYNAMIC_FEATURE_VERSION,
            "trained_at": utils.timestamp(),
            "input_shape": list(train_x.shape[1:]),
            "input_mean": mean.tolist(),
            "input_std": std.tolist(),
            "train_samples": int(len(train_x)),
            "train_classes": int(train_y.max()) + 1,
            "epochs": args.epochs,
            "seed": args.seed,
            "finetuned_on_real_data": bool(args.finetune_real),
            "validation_heldout_writers": validation,
            "validation_skilled_forgeries": forgeries,
            "research_dataset_pairs": real_metrics,
            "final_loss": history["loss"][-1],
            "final_accuracy": history["sparse_categorical_accuracy"][-1],
        },
    )

    dynamic_signature_model.reset()
    log.info("Saved %s (%s)", config.DYNAMIC_MODEL_PATH, version)


if __name__ == "__main__":
    main()


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# train_dynamic_signature_model.py is the training pipeline for the Step-2
# neural model.  It renders synthetic writers and their skilled forgers,
# runs every sample through the production preprocessing and 9-channel
# sequence features, trains the Conv1D + BiGRU + attention embedding with a
# CosFace head and reports three EERs: held-out synthetic writers, held-out
# skilled forgeries, and the real research dataset (kept out of training
# unless --finetune-real).  It saves the .keras model and JSON metadata
# (version, per-channel standardisation, metrics) loaded by the API.
# =============================================================================
