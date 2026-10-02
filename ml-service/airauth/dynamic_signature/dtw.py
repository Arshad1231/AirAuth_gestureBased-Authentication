"""
Dynamic Time Warping distance between multivariate sequences.

Constrained by a Sakoe-Chiba band so that only plausible alignments are
considered.  The final cost is divided by (n + m) so distances do not
depend on length.

Performance: the dynamic programme is inherently sequential along each
row, so instead of looping per *pair*, dtw_batch() runs the recurrence
for many pairs at once — every cell update is a NumPy operation over the
whole batch.  Scoring a probe against 20 templates, or all 190 template
pairs, costs about the same as a single pair.
"""

import numpy as np

from airauth import config


def _band(n, m, band_ratio):
    band_ratio = config.DTW_BAND_RATIO if band_ratio is None else band_ratio
    return max(int(np.ceil(band_ratio * max(n, m))), abs(n - m))


def dtw_batch(sequences_a, sequences_b, band_ratio=None):
    """
    DTW for P pairs at once.

    sequences_a: (P, n, D), sequences_b: (P, m, D)  ->  (P,) distances
    """

    a = np.asarray(sequences_a, dtype=float)
    b = np.asarray(sequences_b, dtype=float)

    pairs, n, _ = a.shape
    m = b.shape[1]
    band = _band(n, m, band_ratio)

    # (P, n, m) Euclidean cost, vectorised.
    cost = np.sqrt(((a[:, :, None, :] - b[:, None, :, :]) ** 2).sum(axis=3))

    previous = np.full((pairs, m + 1), np.inf)
    previous[:, 0] = 0.0

    for i in range(1, n + 1):

        current = np.full((pairs, m + 1), np.inf)
        row = cost[:, i - 1, :]

        for j in range(max(1, i - band), min(m, i + band) + 1):
            current[:, j] = row[:, j - 1] + np.minimum(
                np.minimum(previous[:, j - 1], previous[:, j]), current[:, j - 1]
            )

        previous = current

    return previous[:, m] / (n + m)


def dtw_distance(sequence_a, sequence_b, band_ratio=None):
    """DTW distance between two (T, D) sequences."""

    return float(dtw_batch(np.asarray(sequence_a)[None], np.asarray(sequence_b)[None], band_ratio)[0])


def dtw_one_to_many(probe, references, band_ratio=None):
    """Distances from one (T, D) probe to each of N (T, D) references."""

    references = np.asarray(references, dtype=float)
    probes = np.broadcast_to(np.asarray(probe, dtype=float), references.shape)
    return dtw_batch(probes, references, band_ratio)


def pairwise_dtw(sequences, band_ratio=None):
    """Symmetric (N, N) DTW distance matrix, computed in one batch."""

    sequences = np.asarray(sequences, dtype=float)
    n = len(sequences)
    matrix = np.zeros((n, n))

    if n < 2:
        return matrix

    rows, cols = np.triu_indices(n, k=1)
    distances = dtw_batch(sequences[rows], sequences[cols], band_ratio)
    matrix[rows, cols] = distances
    matrix[cols, rows] = distances

    return matrix


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# dtw.py provides the elastic-matching component of the signature verifier.
# dtw_batch() evaluates the Sakoe-Chiba-banded DTW recurrence for many
# sequence pairs simultaneously (vectorised over the batch), normalised by
# n + m.  dtw_distance() (one pair), dtw_one_to_many() (probe vs. template
# set) and pairwise_dtw() (all enrollment pairs, for consistency checks and
# leave-one-out references) are thin wrappers around it, so live
# verification stays fast even when the template has grown to 20 samples.
# =============================================================================
