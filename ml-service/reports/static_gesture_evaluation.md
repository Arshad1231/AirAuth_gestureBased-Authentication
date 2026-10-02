# Static gesture verifier — evaluation

Generated: 2026-10-02T06:16:58Z  
Embedding model: static-20261002-055446  
Calibration source: synthetic held-out gestures

## synthetic

| comparison | EER | ROC-AUC | FAR @thr | FRR @thr |
|---|---|---|---|---|
| random_impostor | 0.001 | 1.000 | 0.001 | 0.003 |
| shoulder_surfer | 0.377 | 0.645 | 0.997 | 0.003 |
| component_template | 0.012 | 0.999 | - | - |
| component_embedding | 0.002 | 1.000 | - | - |

## Calibration written to models/

* threshold: **3.4192** (min(FAR <= 1.0% bound, 1.25 x genuine 99% quantile))
* fusion weights: {'template': 0.6, 'embedding': 0.4}
* reference priors: {'template': 0.41384, 'embedding': 0.0435}

Note: a shoulder-surfer who copies the exact gesture is only partly
stopped by Step 1 (hand-geometry features).  This is by design — the
static gesture is the *knowledge* factor; Step 2 (the air signature) is
the behavioural biometric that stops copy attacks.
