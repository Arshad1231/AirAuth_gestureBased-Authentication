# AirAuth — Setup Guide (Windows)

Step-by-step instructions to get the project running on a new Windows
machine. All commands are run in **PowerShell** from the project folder:

```powershell
cd "C:\Files\Projects\Capstone V2"
```

---

## 1. Prerequisites

| Tool | Version | Install command | Check |
|---|---|---|---|
| Python | 3.11 | <https://www.python.org/downloads/> (tick **"Add python.exe to PATH"**) | `python --version` |
| Node.js (includes npm) | 18 or newer | `winget install OpenJS.NodeJS.LTS` | `node --version` |
| MongoDB | 6 or newer | `winget install MongoDB.Server` | `Get-Service MongoDB` → **Running** |
| Webcam | any | — | — |
| Browser | Chrome / Edge (recent) | — | — |

> **Important:** after installing Node.js or MongoDB, **close and reopen
> VS Code / PowerShell**. Open terminals keep their old PATH and will
> report `npm is not recognized`. (The project scripts also reload PATH
> automatically, but your own terminal will not.)

**MongoDB alternatives** (pick one if you don't want a local install):

```powershell
# Docker
docker run -d -p 27017:27017 --name airauth-mongo mongo:7

# or MongoDB Atlas (free cluster): copy its connection string into server\.env (step 3)
```

---

## 2. Install the project dependencies (one time)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

This script:

1. creates the Python virtual environment `ml-service\.venv` and installs `ml-service\requirements.txt`
2. checks that Node.js is available
3. creates `server\.env` from `server\.env.example` (if missing)
4. runs `npm install` in `server\` and `client\`

It takes a few minutes (TensorFlow is the largest download).

<details>
<summary>Manual alternative (if you prefer to run each step yourself)</summary>

```powershell
# ML service
cd ml-service
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..

# Backend
cd server
Copy-Item .env.example .env
npm install
cd ..

# Frontend
cd client
npm install
cd ..
```
</details>

---

## 3. Configure the backend

Open `server\.env` and check these values:

| Variable | What to set |
|---|---|
| `MONGODB_URI` | `mongodb://127.0.0.1:27017/airauth` for a local/Docker MongoDB, or your Atlas connection string |
| `JWT_SECRET` | any long random string (used to sign login tokens) |
| `ML_SERVICE_URL` | leave as `http://127.0.0.1:8000` |
| `ML_SERVICE_API_KEY` | leave as is (must match the ML service; default `dev-ml-service-key`) |

Generate a random secret if you need one:

```powershell
-join ((1..48) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })
```

---

## 4. AI models

Trained models and their calibration are **already included** in
`ml-service\models\` — nothing to do for a first run.

To retrain and recalibrate both models from scratch (≈ 15 minutes):

```powershell
cd ml-service
.\.venv\Scripts\python.exe -m pipelines.run_full_pipeline
cd ..
```

Quick smoke test of the pipelines (small data, ≈ 3 minutes — **overwrites**
the models with low-quality ones, so re-run the full pipeline afterwards):

```powershell
.\.venv\Scripts\python.exe -m pipelines.run_full_pipeline --quick
```

---

## 5. Run the application

### Option A — one command

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-dev.ps1
```

Three windows open:

| Window | Service | URL | Ready when you see |
|---|---|---|---|
| 1 | AI / ML service (FastAPI) | <http://127.0.0.1:8000/docs> | `Application startup complete` |
| 2 | Backend API (Express) | <http://localhost:5000/api/system/health> | `[db] connected` and `listening on http://localhost:5000` |
| 3 | Website (React + Vite) | <http://localhost:5173> | `Local: http://localhost:5173/` |

### Option B — three terminals manually

```powershell
# Terminal 1 — AI service
cd ml-service
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — backend
cd server
npm run dev

# Terminal 3 — website
cd client
npm run dev
```

Open **<http://localhost:5173>** and allow camera access. To stop, close
the windows (or press `Ctrl+C` in each terminal).

---

## 6. Check that everything works

1. The home page **status panel** shows API, MongoDB and ML service with green dots, and both model versions.
2. **Register** a user:
   * pick a username
   * Step 1: show the **same** secret hand gesture 5 times (same hand, hold it still until the bar fills)
   * Step 2: sign in the air with your index finger 8 times — hold the finger still for ~1 s to finish each one
3. **Log in** with that username: gesture → air signature → **ACCESS GRANTED** → dashboard.
4. Try logging in with an unknown username — you are redirected to registration.

Automated tests for the AI service:

```powershell
cd ml-service
.\.venv\Scripts\python.exe -m pytest tests -q      # expect: 23 passed
```

---

## 7. Troubleshooting

| Problem | Cause / fix |
|---|---|
| `npm` / `node` is not recognized | Node.js missing, or the terminal was opened before installing it → install Node.js, then **restart VS Code / PowerShell** |
| `running scripts is disabled on this system` | Run scripts with `powershell -ExecutionPolicy Bypass -File scripts\...` as shown above |
| API window: `could not connect to mongodb://...` | MongoDB is not running → `net start MongoDB` (admin terminal), start the Docker container, or fix `MONGODB_URI` |
| Status panel: ML service *unavailable* | Window 1 is not running or crashed — read its error; make sure port 8000 is free |
| Status panel: model *not trained* | `ml-service\models\*.keras` missing → run the full pipeline (section 4) |
| `Address already in use` / port busy | Another copy is still running → close old windows, or find it with `netstat -ano \| findstr :5000` |
| Camera does not start | Allow camera permission in the browser (lock icon in the address bar); close other apps using the webcam |
| "Your hand moved while capturing" | Hold the gesture completely still until the progress bar is full |
| "The signature was too short" | Draw larger and longer; keep the hand in view until you finish |
| Gesture/signature keeps failing | Use good lighting, the same hand and the same distance as at registration; re-register if needed |
| `Account temporarily locked` | 5 failed attempts in a row → wait 15 minutes (set in `server\.env`: `LOCKOUT_MINUTES`) |
| First AI-service start is slow | Normal: TensorFlow loads and compiles both models (≈ 5–15 s) |

---

## 8. Project layout (for orientation)

```
Capstone V2/
├── SETUP.md            ← this guide
├── README.md           ← project overview
├── Architecture/       ← system & model architecture documents
├── client/             ← React website           (npm run dev → :5173)
├── server/             ← Express + MongoDB API     (npm run dev → :5000)
├── ml-service/         ← Python AI service         (uvicorn      → :8000)
│   └── data/research_signatures/  ← recorded research dataset (3 users)
└── scripts/            ← setup.ps1, start-dev.ps1
```

Next: read `Architecture/05_Project_Flow.md` for the demo script and
roadmap.

<!--
=============================================================================
FILE SUMMARY
-----------------------------------------------------------------------------
SETUP.md is the practical installation guide for Windows: prerequisites
(Python, Node.js, MongoDB and alternatives, with the PATH-refresh caveat),
installing dependencies via scripts/setup.ps1 or manually, configuring
server/.env, the included / retrainable AI models, starting the three
services (one script or three terminals), verifying the system with a
first registration + login and the test suite, a troubleshooting table and
a short folder map.
=============================================================================
-->
