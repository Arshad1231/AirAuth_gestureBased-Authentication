"""
Biometric verification metrics computed from distance scores.

Convention: LOWER distance = more likely genuine.  A probe is ACCEPTED
when distance <= threshold.
"""

import numpy as np


def far_frr_at(genuine, impostor, threshold):
    """False Acceptance Rate and False Rejection Rate at one threshold."""

    genuine = np.asarray(genuine, dtype=float)
    impostor = np.asarray(impostor, dtype=float)

    frr = float(np.mean(genuine > threshold)) if genuine.size else 0.0
    far = float(np.mean(impostor <= threshold)) if impostor.size else 0.0

    return far, frr


def compute_eer(genuine, impostor):
    """
    Equal Error Rate.

    Sweeps every observed score as a candidate threshold and returns the
    point where FAR and FRR are closest.
    """

    genuine = np.asarray(genuine, dtype=float)
    impostor = np.asarray(impostor, dtype=float)

    if genuine.size == 0 or impostor.size == 0:
        raise ValueError("Both genuine and impostor scores are required.")

    candidates = np.unique(np.concatenate([genuine, impostor]))

    best = None

    for threshold in candidates:
        far, frr = far_frr_at(genuine, impostor, threshold)
        gap = abs(far - frr)

        if best is None or gap < best["gap"]:
            best = {
                "gap": gap,
                "threshold": float(threshold),
                "far": far,
                "frr": frr,
                "eer": (far + frr) / 2.0,
            }

    best.pop("gap")
    return best


def threshold_for_far(genuine, impostor, target_far):
    """Largest threshold whose FAR does not exceed target_far."""

    impostor = np.sort(np.asarray(impostor, dtype=float))

    if impostor.size == 0:
        raise ValueError("Impostor scores are required.")

    allowed = int(np.floor(target_far * impostor.size))

    if allowed <= 0:
        threshold = float(impostor[0]) - 1e-9
    else:
        threshold = float(impostor[allowed - 1])

    far, frr = far_frr_at(genuine, impostor, threshold)

    return {"threshold": threshold, "far": far, "frr": frr}


def threshold_for_frr(genuine, target_frr):
    """Strictest threshold that still accepts (1 - target_frr) of genuine scores."""

    genuine = np.asarray(genuine, dtype=float)

    if genuine.size == 0:
        raise ValueError("Genuine scores are required.")

    return float(np.quantile(genuine, 1.0 - target_frr))


def roc_auc(genuine, impostor):
    """
    ROC-AUC via the Mann-Whitney statistic: probability that a random
    impostor distance is larger than a random genuine distance.
    """

    genuine = np.asarray(genuine, dtype=float)
    impostor = np.asarray(impostor, dtype=float)

    if genuine.size == 0 or impostor.size == 0:
        return float("nan")

    greater = (impostor[None, :] > genuine[:, None]).sum()
    ties = (impostor[None, :] == genuine[:, None]).sum()

    return float((greater + 0.5 * ties) / (genuine.size * impostor.size))


def summarize(genuine, impostor, operating_threshold=None):
    """One dictionary with every metric the evaluation reports need."""

    eer = compute_eer(genuine, impostor)

    summary = {
        "genuine_trials": int(np.size(genuine)),
        "impostor_trials": int(np.size(impostor)),
        "genuine_mean": float(np.mean(genuine)),
        "impostor_mean": float(np.mean(impostor)),
        "eer": eer["eer"],
        "eer_threshold": eer["threshold"],
        "roc_auc": roc_auc(genuine, impostor),
    }

    if operating_threshold is not None:
        far, frr = far_frr_at(genuine, impostor, operating_threshold)
        summary.update(
            {
                "operating_threshold": float(operating_threshold),
                "operating_far": far,
                "operating_frr": frr,
            }
        )

    return summary


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# metrics.py implements the standard biometric evaluation metrics on
# distance scores (lower = genuine):
#   far_frr_at()        FAR / FRR at a fixed threshold
#   compute_eer()       Equal Error Rate and the threshold where it occurs
#   threshold_for_far() loosest threshold whose FAR stays within a target
#   threshold_for_frr() strictest threshold that keeps FRR within a target
#   roc_auc()           ROC-AUC through the Mann-Whitney U statistic
#   summarize()         bundle of all of the above for reports
# It is pure NumPy so it works without scikit-learn.
# =============================================================================
