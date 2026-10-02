# Dynamic signature verifier — evaluation

Generated: 2026-10-02T06:22:09Z  
Embedding model: dynamic-20261002-060233  
Users: 3, signatures: 90

Impostor trials are *random forgeries* (other users' own signatures).

## Protocol: web_registration

Genuine trials: 60, impostor trials: 120

| Score | EER | ROC-AUC | genuine mean | impostor mean |
|---|---|---|---|---|
| dtw | 0.133 | 0.913 | 0.0340 | 0.0663 |
| embedding | 0.267 | 0.813 | 0.4932 | 0.7198 |
| global | 0.217 | 0.862 | 1.0110 | 1.4833 |
| **fused** | 0.083 | 0.943 | 1.0136 | 1.7324 |

At the calibrated threshold 1.253: FAR = 0.050, FRR = 0.167

## Protocol: multi_session

Genuine trials: 90, impostor trials: 180

| Score | EER | ROC-AUC | genuine mean | impostor mean |
|---|---|---|---|---|
| dtw | 0.144 | 0.889 | 0.0332 | 0.0652 |
| embedding | 0.189 | 0.877 | 0.4500 | 0.7371 |
| global | 0.133 | 0.899 | 0.8028 | 1.2867 |
| **fused** | 0.144 | 0.899 | 1.0631 | 1.9184 |

At the calibrated threshold 1.253: FAR = 0.039, FRR = 0.222

## Calibration written to models/

* threshold: **1.2534** (FAR <= 5% on web_registration)
* fusion weights: {'dtw': 0.45, 'embedding': 0.35, 'global': 0.2}
* reference priors: {'dtw': 0.03536, 'embedding': 0.43768, 'global': 0.8903}

## Fusion-weight search (web_registration, informational)

| weights | EER | ROC-AUC |
|---|---|---|
| {'dtw': 0.4, 'embedding': 0.2, 'global': 0.4} | 0.083 | 0.948 |
| {'dtw': 0.6, 'embedding': 0.2, 'global': 0.2} | 0.083 | 0.947 |
| {'dtw': 0.8, 'embedding': 0.2, 'global': 0.0} | 0.083 | 0.943 |
| {'dtw': 0.4, 'embedding': 0.4, 'global': 0.2} | 0.083 | 0.941 |
| {'dtw': 0.8, 'embedding': 0.0, 'global': 0.2} | 0.087 | 0.946 |
| {'dtw': 0.6, 'embedding': 0.0, 'global': 0.4} | 0.100 | 0.945 |
| {'dtw': 1.0, 'embedding': 0.0, 'global': 0.0} | 0.100 | 0.939 |
| {'dtw': 0.4, 'embedding': 0.0, 'global': 0.6} | 0.100 | 0.939 |
