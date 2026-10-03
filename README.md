# AirAuth — Two-Step Air Authentication

Password-less login with a webcam, in two AI-verified steps:

1. **Static hand gesture** — hold your secret hand pose. 21 MediaPipe key-points →
   115 geometric features → template matcher + neural pose embedding.
2. **Dynamic air signature** — sign in the air with your index finger. The
   trajectory's shape *and* motion → DTW + behavioural statistics + a
   Conv1D-BiGRU-attention embedding network.

Access is granted only when both steps pass, in order. Unregistered users
are sent to registration, which enrolls both factors.

**Stack:** MongoDB · Express · React · Node.js + a Python FastAPI ML service.

```
client/        React + Vite UI, on-device MediaPipe hand tracking (no video leaves the browser)
server/        Express + Mongoose API: accounts, 2-step login state machine, lockout, audit
ml-service/    Python AI service: preprocessing, features, models, pipelines, tests
Architecture/  Architecture & model documents (start here)
scripts/       setup.ps1, start-dev.ps1
```

## Quick start (Windows)

Full step-by-step instructions and troubleshooting: **[SETUP.md](SETUP.md)**.

Prerequisites: Python 3.11, **Node.js 18+**, **MongoDB** (local, Docker or Atlas).

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1      # install everything
# edit server\.env  (MONGODB_URI, JWT_SECRET)
powershell -ExecutionPolicy Bypass -File scripts\start-dev.ps1  # start all three services
# open http://localhost:5173
```

Retrain / recalibrate the models (trained models are already included):

```powershell
cd ml-service
.\.venv\Scripts\python.exe -m pipelines.run_full_pipeline
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Current results

| Step | Data | Result |
|---|---|---|
| 1 Gesture | 150 simulated users, gestures unseen in training | EER 0.1 % vs random impostors |
| 2 Signature | real research dataset, 8-signature enrollment, later sessions | EER 8.3 %, AUC 0.94; FAR 5 % / FRR 17 % at the live threshold |

See `ml-service/reports/` for full tables and `Architecture/05_Project_Flow.md`
for setup, the demo script and next steps.

## Documentation

| Document | Content |
|---|---|
| [01_System_Architecture](Architecture/01_System_Architecture.md) | MERN + ML architecture, flows, data model, security |
| [02_Static_Gesture_Model](Architecture/02_Static_Gesture_Model.md) | Step 1 features, network, decision rule, results |
| [03_Dynamic_Signature_Model](Architecture/03_Dynamic_Signature_Model.md) | Step 2 preprocessing, features, network, results |
| [04_ML_Pipelines](Architecture/04_ML_Pipelines.md) | Training, evaluation, calibration, retraining loop |
| [05_Project_Flow](Architecture/05_Project_Flow.md) | What to do, in order — setup, run, demo, roadmap |
| [06_AI_Models_Explained](Architecture/06_AI_Models_Explained.md) | Plain-language guide: every model and technique, why it was chosen, why it beats the alternatives |

<!--
=============================================================================
FILE SUMMARY
-----------------------------------------------------------------------------
README.md is the entry point of the repository: what AirAuth does (static
gesture + dynamic air signature), the folder layout, Windows quick-start
commands, how to retrain and test the models, the headline results and links
to the five architecture documents.
=============================================================================
-->
