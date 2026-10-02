"""
MASTER PIPELINE — trains, evaluates and calibrates both models in order.

    1. train_static_gesture_model        -> models/static_gesture_embedding.*
    2. train_dynamic_signature_model     -> models/dynamic_signature_embedding.*
    3. evaluate_static_gesture_model     -> models/static_gesture_calibration.json
    4. evaluate_dynamic_signature_model  -> models/dynamic_signature_calibration.json

Evaluation must run AFTER training because the calibrated threshold
depends on the exact model weights.

Usage (from ml-service/):
    python -m pipelines.run_full_pipeline
    python -m pipelines.run_full_pipeline --skip-training      # recalibrate only
    python -m pipelines.run_full_pipeline --quick              # smoke test
    python -m pipelines.run_full_pipeline --use-collected      # include web-app data
"""

import argparse

from pipelines import (
    evaluate_dynamic_signature_model,
    evaluate_static_gesture_model,
    pipeline_utils as utils,
    train_dynamic_signature_model,
    train_static_gesture_model,
)


def main(argv=None):

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-training", action="store_true")
    parser.add_argument("--quick", action="store_true", help="tiny datasets / epochs for a smoke test")
    parser.add_argument("--use-collected", action="store_true",
                        help="train on real samples exported from MongoDB as well")
    args = parser.parse_args(argv)

    log = utils.setup_logging()

    static_args, dynamic_args, static_eval_args = [], [], []

    if args.quick:
        static_args += ["--instances", "6", "--epochs", "2"]
        dynamic_args += ["--writers", "40", "--renders", "4", "--epochs", "2"]
        static_eval_args += ["--users", "20", "--impostors-per-user", "4"]

    if args.use_collected:
        static_args.append("--collected")
        dynamic_args.append("--finetune-real")

    steps = []
    if not args.skip_training:
        steps += [
            ("Train static gesture model", train_static_gesture_model.main, static_args),
            ("Train dynamic signature model", train_dynamic_signature_model.main, dynamic_args),
        ]
    steps += [
        ("Evaluate + calibrate static gesture", evaluate_static_gesture_model.main, static_eval_args),
        ("Evaluate + calibrate dynamic signature", evaluate_dynamic_signature_model.main, []),
    ]

    for number, (title, function, step_args) in enumerate(steps, start=1):
        log.info("=" * 70)
        log.info("STEP %d/%d  %s %s", number, len(steps), title, " ".join(step_args))
        log.info("=" * 70)
        with utils.Timer() as timer:
            function(step_args)
        log.info("STEP %d finished in %.1fs", number, timer.seconds)

    log.info("All steps complete. Reports are in ml-service/reports/.")


if __name__ == "__main__":
    main()


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# run_full_pipeline.py is the one-command entry point for the ML lifecycle:
# it runs the two training pipelines and then the two evaluation/calibration
# pipelines in the required order, with flags for recalibration only
# (--skip-training), a fast smoke test (--quick) and retraining on real data
# exported from the web app (--use-collected).
# =============================================================================
