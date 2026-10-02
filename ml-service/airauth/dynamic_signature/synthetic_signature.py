"""
Synthetic in-air signature generator for pretraining the signature
embedding network.

Why it exists
-------------
The research dataset has 3 users — far too few for a deep network to
learn what makes two signatures "the same writer".  Synthetic writers
give the network thousands of identities to learn from; the real data is
kept for *evaluation and calibration* (and optional fine-tuning once more
users have been collected through the web app).

Model of a writer
-----------------
    shape     70 %: 5–13 control points from a random walk with sharp
              turns / loops;  30 %: a closed figure traced back to its
              start (the research dataset contains such shapes);
              joined by a Catmull-Rom spline
    rhythm    pen speed follows the 2/3 power law of human motor control
              (v ∝ curvature^-β, β writer-specific) modulated by a few
              writer-specific sinusoids (individual accelerations/pauses)
    tempo     total duration 1.5–4.5 s

Each rendering of a writer adds natural variation: control-point jitter,
small rotation/scale/shear, tempo change, rhythm phase noise, camera
frame-rate jitter, MediaPipe-like tracking noise, an occasional spike
and idle dwell at both ends.

Skilled forgers
---------------
make_forger() copies a writer's shape (with more jitter) but draws it
with their *own* rhythm and a slower tempo.  Forgers are separate classes
during training, which forces the network to use dynamics — not only
shape — to tell people apart.
"""

import numpy as np


def _catmull_rom(points, samples_per_segment=24):

    padded = np.vstack([points[0], points, points[-1]])
    curve = []
    t = np.linspace(0, 1, samples_per_segment, endpoint=False)[:, None]

    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        curve.append(
            0.5 * (
                2 * p1
                + (-p0 + p2) * t
                + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3
            )
        )

    curve.append(points[-1][None, :])
    return np.vstack(curve)


class SyntheticSignatureGenerator:

    def __init__(self, seed=0):
        self.rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # IDENTITIES
    # ------------------------------------------------------------------

    def _rhythm(self):
        rng = self.rng
        return {
            "beta": rng.uniform(0.15, 0.40),
            "amplitudes": rng.uniform(0.0, 0.45, 3),
            "frequencies": rng.uniform(1.0, 7.0, 3),
            "phases": rng.uniform(0, 2 * np.pi, 3),
        }

    def make_writer(self):

        rng = self.rng

        if rng.random() < 0.3:
            # Closed figure (loop / polygon-like), traced back to the start.
            count = int(rng.integers(3, 8))
            angles = np.sort(rng.uniform(0, 2 * np.pi, count)) * rng.choice([-1, 1])
            radii = rng.uniform(0.6, 1.0, count)
            control = np.column_stack([radii * np.cos(angles), radii * np.sin(angles)])
            control = np.vstack([control, control[:1]])
        else:
            count = int(rng.integers(5, 14))
            angle = rng.uniform(0, 2 * np.pi)
            points = [np.zeros(2)]

            for _ in range(count - 1):
                angle += rng.normal(0, 1.3)
                step = rng.uniform(0.25, 0.8)
                points.append(points[-1] + step * np.array([np.cos(angle), np.sin(angle)]))

            control = np.array(points)
        control -= control.mean(axis=0)
        control /= np.abs(control).max() + 1e-9

        return {
            "control": control,
            "duration": rng.uniform(1.5, 4.5),
            "rhythm": self._rhythm(),
        }

    def make_forger(self, writer):

        rng = self.rng

        return {
            "control": writer["control"] + rng.normal(0, 0.06, writer["control"].shape),
            "duration": writer["duration"] * rng.uniform(1.15, 1.8),
            "rhythm": self._rhythm(),
        }

    # ------------------------------------------------------------------
    # RENDERING
    # ------------------------------------------------------------------

    def render(self, identity, variation=1.0):
        """
        One recorded attempt -> API-shaped sample
        {"points": [[t, x, y, z]], "width": 1, "height": 1}.
        """

        rng = self.rng

        control = identity["control"] + rng.normal(0, 0.035 * variation, identity["control"].shape)

        theta = np.deg2rad(rng.normal(0, 6 * variation))
        rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
        scale = np.diag(rng.normal(1.0, 0.05 * variation, 2)) * rng.normal(1.0, 0.08 * variation)
        shear = np.array([[1.0, rng.normal(0, 0.05 * variation)], [0.0, 1.0]])
        control = control @ (rotation @ scale @ shear).T

        curve = _catmull_rom(control)

        steps = np.linalg.norm(np.diff(curve, axis=0), axis=1)
        steps = np.maximum(steps, 1e-6)
        s = np.concatenate([[0.0], np.cumsum(steps)])
        s /= s[-1]

        # Curvature on the dense curve (turning angle per unit length).
        direction = np.unwrap(np.arctan2(*np.diff(curve, axis=0).T[::-1]))
        turning = np.abs(np.gradient(direction)) / steps
        turning = np.convolve(turning, np.ones(5) / 5, mode="same")

        rhythm = identity["rhythm"]
        mid_s = 0.5 * (s[1:] + s[:-1])
        modulation = 1.0 + np.sum(
            rhythm["amplitudes"][:, None]
            * np.sin(
                2 * np.pi * rhythm["frequencies"][:, None] * mid_s[None, :]
                + rhythm["phases"][:, None]
                + rng.normal(0, 0.3 * variation, (3, 1))
            ),
            axis=0,
        )
        speed = (turning + 0.5) ** (-rhythm["beta"]) * np.clip(modulation, 0.15, None)

        dt = steps / speed
        t = np.concatenate([[0.0], np.cumsum(dt)])
        t *= identity["duration"] * rng.normal(1.0, 0.08 * variation) / t[-1]

        fps = rng.uniform(24, 31)
        frame_times = np.arange(0.0, t[-1], 1.0 / fps)
        frame_times = np.sort(frame_times + rng.normal(0, 0.15 / fps, len(frame_times)))
        frame_times = np.clip(frame_times, 0.0, t[-1])

        x = np.interp(frame_times, t, curve[:, 0])
        y = np.interp(frame_times, t, curve[:, 1])

        size = rng.uniform(0.12, 0.22)
        centre = rng.uniform(0.35, 0.65, 2)
        noise = rng.uniform(0.0003, 0.0012)
        x = centre[0] + size * x + rng.normal(0, noise, len(x))
        y = centre[1] - size * y + rng.normal(0, noise, len(y))

        if rng.random() < 0.3 and len(x) > 4:
            spike = int(rng.integers(1, len(x) - 1))
            x[spike] += rng.normal(0, 0.04)
            y[spike] += rng.normal(0, 0.04)

        # Idle dwell before / after drawing (removed again by trim_idle).
        lead = int(rng.integers(2, 8))
        tail = int(rng.integers(2, 8))
        frame_dt = 1.0 / fps

        lead_t = -frame_dt * np.arange(lead, 0, -1)
        tail_t = frame_times[-1] + frame_dt * np.arange(1, tail + 1)

        times = np.concatenate([lead_t, frame_times, tail_t]) - (lead_t[0] if lead else 0.0)
        xs = np.concatenate([x[0] + rng.normal(0, 0.0008, lead), x, x[-1] + rng.normal(0, 0.0008, tail)])
        ys = np.concatenate([y[0] + rng.normal(0, 0.0008, lead), y, y[-1] + rng.normal(0, 0.0008, tail)])

        points = np.column_stack([times, xs, ys, np.zeros_like(xs)])

        return {"points": points.tolist(), "width": 1, "height": 1}


# =============================================================================
# FILE SUMMARY
# -----------------------------------------------------------------------------
# synthetic_signature.py generates unlimited labelled air signatures for
# pretraining the Step-2 embedding network.  A writer is a random-walk
# control polygon (Catmull-Rom spline), a tempo and a personal rhythm (2/3
# power-law speed model with writer-specific modulation).  render() adds
# realistic per-attempt variation, camera sampling, tracking noise, spikes
# and idle dwell, and returns the same JSON format as the browser so the
# production preprocessing runs unchanged.  make_forger() creates skilled-
# forgery identities that copy a shape with a different rhythm, teaching the
# network that *how* a signature is drawn matters, not only its shape.
# =============================================================================
