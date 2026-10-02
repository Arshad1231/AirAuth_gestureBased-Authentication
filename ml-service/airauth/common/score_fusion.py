"""
User-normalised score fusion shared by both authentication steps.

Each verifier produces several raw distances ("components") between the
probe and the user's enrollment samples.  Raw distances are not comparable
across users (some people sign more consistently than others), so every
component is divided by an effective reference that blends the user's own
*reference distance* (average leave-one-out distance between their
enrollment samples) with a population *prior*:

    user_ref_c   = max(reference_c, floor_c)
    effective_c  = user_ref_c ** blend * prior_c ** (1 - blend)
    normalised_c = raw_c / effective_c
    fused        = sum_c w_c * normalised_c / sum_c w_c

blend = 1 is full per-user normalisation, blend = 0 ignores the user.
On the research dataset a blend of 0.5 was the most robust choice: with
only a handful of enrollment samples the user's own reference is noisy,
so it is shrunk towards the population value.
"""

import numpy as np


def leave_one_out_reference(pairwise_distance_matrix):
    """
    Mean distance from each enrollment sample to the remaining samples.

    pairwise_distance_matrix: (N, N) symmetric matrix with zeros on the
    diagonal.
    """

    matrix = np.asarray(pairwise_distance_matrix, dtype=float)
    n = matrix.shape[0]

    if n < 2:
        return 0.0

    off_diagonal = matrix[~np.eye(n, dtype=bool)]

    return float(np.mean(off_diagonal))


def effective_reference(reference, floor, prior=None, blend=1.0):
    user_reference = max(float(reference), float(floor))
    if prior is None or blend >= 1.0:
        return user_reference
    return user_reference ** blend * float(prior) ** (1.0 - blend)


def fuse(raw_distances, references, floors, weights, priors=None, blend=1.0):
    """
    Combine component distances into one normalised score.

    Components missing from raw_distances (e.g. the neural embedding when
    no trained model is available) are skipped and the remaining weights
    are re-normalised.
    """

    normalised = {}
    total_weight = 0.0
    fused = 0.0
    priors = priors or {}

    for name, raw in raw_distances.items():

        if raw is None or weights.get(name, 0.0) <= 0.0:
            continue

        reference = effective_reference(
            references.get(name, 0.0), floors[name], priors.get(name), blend
        )
        value = float(raw) / reference

        normalised[name] = value
        fused += weights[name] * value
        total_weight += weights[name]

    if total_weight == 0:
        raise ValueError("No score components available for fusion.")

    return fused / total_weight, normalised


def match_percentage(fused_score, threshold):
    """
    Human-friendly 0-100 match score for the UI.

    fused == 0          -> 100 %
    fused == threshold  ->  50 %
    fused >= 2*threshold ->  0 %
    """

    ratio = float(fused_score) / float(threshold)

    return float(np.clip(100.0 * (1.0 - ratio / 2.0), 0.0, 100.0))


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# score_fusion.py turns several raw distances into a single decision score.
#   leave_one_out_reference()  measures how much a user naturally varies
#                              between their own enrollment samples
#   effective_reference()      floors the user's reference and blends it with
#                              a population prior (shrinkage for small
#                              enrollment sets)
#   fuse()                     divides every component by that effective
#                              reference, then takes a weighted mean,
#                              silently skipping unavailable components
#   match_percentage()         maps the fused score to a 0-100 % value for
#                              display (50 % == exactly at threshold)
# Used by both static_gesture/verifier.py and dynamic_signature/verifier.py.
# =============================================================================
