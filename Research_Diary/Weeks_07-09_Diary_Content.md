# Research Diary — Content for Weeks 7, 8 and 9

**Project:** AirAuth — Two-Step Air Authentication (Static Hand Gesture + Dynamic Air Signature)
**Diary phases covered:**
- Week 7, Week 8 → *Phase 3 · Requirements, Concept Selection & System Design* (diary pp. 29–44)
- Week 9 → *Phase 4 · Implementation & Unit Testing (O1–O2)* (diary pp. 45–56)

> **How to use this:** copy the text into the matching boxes by hand. Replace every
> `[ ... ]` with your real details (names, IDs, dates). Write only what your team
> actually did — if the split of work below differs from reality, change it.
> **Do not fill the "Guide Feedback / Comments" box yourself** — that is the
> guide's record of the meeting. Below each week you get *points to raise with
> the guide* instead.

---

## 0. First: the five objectives (needed on diary pp. 9 & 14)

Every week references O1–O5, so fix these first (Section 0 "The five objectives" and Section 1 Traceability Matrix).

| ID | Objective | Measurable success criterion | Sem | Deliverable |
|---|---|---|---|---|
| **O1** | Static hand-gesture capture & verification (Step 1) | 21-landmark capture in browser; gesture verifier EER ≤ 2 % vs random impostors on held-out gestures | VII | `ml-service/airauth/static_gesture/`, tests |
| **O2** | Dynamic air-signature capture & verification (Step 2) | Fingertip trajectory capture; DTW + behavioural verifier EER ≤ 15 % on research dataset (8-sample enrollment) | VII | `ml-service/airauth/dynamic_signature/`, tests |
| **O3** | Deep embedding models + training / calibration pipelines | Two trained embedding networks; one-command pipeline; calibrated thresholds saved | VIII | `ml-service/pipelines/`, `models/` |
| **O4** | MERN web application with two-step login | Register → Step 1 → Step 2 → access granted; lockout, rate limit, JWT; end-to-end tests pass | VIII | `client/`, `server/` |
| **O5** | System evaluation, security & real-user validation | FAR / FRR / EER / ROC-AUC reports; replay & step-skip protection; ≥ 10 real users evaluated | VIII | `reports/`, Architecture docs |

---

# WEEK 07 — Phase 3 · Requirements, Concept Selection & Design

### Header
| Field | Write |
|---|---|
| Week No. | 07 |
| Phase | Phase 3 — Requirements, Concept Selection & Design |
| Dates (from – to) | `[dd/mm/yyyy – dd/mm/yyyy]` |
| Planned agenda / focus | Act on Review 1 feedback; write the requirements specification (3.1); list constraints & standards (3.2); generate candidate solutions (3.3) and score them in a decision matrix (3.4). |

### Member-wise work
| Member | Tasks undertaken this week | Prog. % |
|---|---|---|
| 1. `[Name]` (ML / vision lead) | Wrote ML-side functional & non-functional requirements (accuracy, latency, enrollment size); studied MediaPipe HandLandmarker output format (21 landmarks, handedness). | 100 |
| 2. `[Name]` (backend lead) | Wrote security & data requirements (two-step order, lockout, JWT, data deletion); listed applicable standards (ISO 29148, 25010, 27001/OWASP, DPDP Act). | 100 |
| 3. `[Name]` (frontend lead) | Wrote usability requirements (capture UX, countdowns, auto-stop); drafted 3 candidate concepts and the weighted decision matrix with the team. | 100 |

### Actionable items completed
- Requirements specification (3.1) — 16 requirements, each traced to O1–O5.
- Constraints & standards table (3.2).
- Three candidate concepts compared (3.3) and decision matrix completed (3.4); **Concept B selected**.

### Challenges faced & how addressed
- *No public dataset of "personal" hand gestures* → decided to use metric learning with a synthetic hand generator for training, and keep real data for testing.
- *Only 3 real users in our signature dataset* → requirement for template adaptation and a data-export pipeline to collect real users later.

### Evidence produced
Requirements table (diary p. 30), decision matrix (p. 33), `Architecture/01_System_Architecture.md` (draft).

### Action plan for next week
| Task | Expected outcome | Owner | Due |
|---|---|---|---|
| Draw architecture, data-flow and component diagrams | 3.5(a)(b)(c) complete | `[M2]` | `[date]` |
| Detailed design of O1 & O2 components | 3.6 table complete | `[M1]` | `[date]` |
| Risk register + work-breakdown plan | 3.7, 3.8 complete | `[M3]` | `[date]` |

### Points to raise with the guide (guide writes the feedback box)
- Approval of the five objectives and success criteria.
- Is synthetic training data acceptable if evaluation is on real data?
- Confirm the standards list for Gate review.

---

## Sections to fill during Week 7

### 3.1 Requirements specification (diary p. 30)

| Req. ID | Type | Requirement | Traces to |
|---|---|---|---|
| FR-01 | Functional | Capture 21 hand landmarks per frame from a standard webcam in the browser | O1 |
| FR-02 | Functional | Register a static gesture from 5 captures of the same pose | O1 |
| FR-03 | Functional | Verify a static gesture; reject wrong hand and different gesture | O1 |
| FR-04 | Functional | Capture index-fingertip trajectory (t, x, y) with auto-stop | O2 |
| FR-05 | Functional | Register an air signature from 8 samples | O2 |
| FR-06 | Functional | Verify an air signature using shape and motion | O2 |
| FR-07 | Functional | Login must be Step 1 then Step 2; Step 2 cannot be skipped | O4 |
| FR-08 | Functional | Unregistered usernames are redirected to registration | O4 |
| FR-09 | Functional | User can view login history and delete all biometric data | O4 |
| FR-10 | Functional | Retrain / recalibrate models from collected data with one command | O3 |
| NFR-01 | Non-functional (performance) | Verification response < 1 s | O1, O2 |
| NFR-02 | Non-functional (accuracy) | Gesture EER ≤ 2 %; signature EER ≤ 15 % | O1, O2, O5 |
| NFR-03 | Non-functional (security) | Lock account after 5 failures; rate limiting; reject replayed data | O4, O5 |
| NFR-04 | Non-functional (privacy) | Video never leaves the browser; templates never sent to client | O4 |
| NFR-05 | Non-functional (hardware) | Works with an ordinary laptop webcam, CPU only | O1, O2 |
| NFR-06 | Non-functional (maintainability) | Modular services; automated tests for ML and API | O3, O4 |

### 3.2 Constraints & standards (diary p. 31)

| Constraint / standard | Type | How it shapes the design |
|---|---|---|
| Ordinary webcam, no depth sensor | Hardware | Use MediaPipe 2-D landmarks; z treated as noisy (low weight / dropped) |
| CPU-only machines | Hardware | Small networks (~100k params), graph-compiled inference |
| Very small real dataset (3 users) | Data | Synthetic pretraining; real data reserved for evaluation |
| Two-semester timeline | Schedule | Non-neural verifiers first (O1, O2), neural models in CP2 (O3) |
| ISO/IEC/IEEE 29148 | Standard | Requirements written with IDs and traceability |
| ISO/IEC/IEEE 42010 | Standard | Architecture described in views (deployment, data-flow, component) |
| ISO/IEC 25010 | Standard | Quality attributes: performance, security, usability, maintainability |
| ISO/IEC 27001 / OWASP Top 10 | Standard | Auth, rate limiting, input validation, secrets in `.env` |
| ISO/IEC/IEEE 29119 | Standard | Unit → integration → system test plan with test IDs |
| India DPDP Act 2023 / GDPR | Legal | Consent, purpose limitation, right to delete biometric data |
| ACM/IEEE-CS Code of Ethics | Ethics | Honest reporting of accuracy limits; no real banking data |

### 3.3 Candidate solutions (diary p. 32)

| Concept | Description | Pros | Cons |
|---|---|---|---|
| A | Single-factor air signature, desktop OpenCV app (our research baseline) | Simple; already prototyped | One factor only; not a web app; no user management |
| **B** | **Two-step: static gesture + air signature; React web app with in-browser MediaPipe; Express + MongoDB; Python ML micro-service** | Two factors; private (no video upload); any webcam; modular | More components to build and integrate |
| C | Server-side video upload, end-to-end deep CNN/LSTM on raw frames | Potentially high accuracy with big data | Needs large dataset + GPU; privacy risk; slow |
| D | Password + air signature | Familiar | Passwords are the problem we want to remove |
| E | Depth-camera / Leap Motion gesture auth | Accurate 3-D data | Special hardware; not deployable to normal users |

### 3.4 Decision / trade-off matrix (diary p. 33)
Score 1 (poor) – 5 (excellent); weighted score = weight × score.

| Criterion | Weight | Concept A | Concept B | Concept C |
|---|---|---|---|---|
| Security (factors, attack resistance) | 0.20 | 2 | 5 | 3 |
| Accuracy with small data | 0.15 | 3 | 4 | 1 |
| Privacy | 0.15 | 4 | 5 | 1 |
| Hardware cost / accessibility | 0.10 | 4 | 5 | 2 |
| Latency | 0.10 | 4 | 4 | 2 |
| Feasibility in 2 semesters | 0.15 | 5 | 4 | 2 |
| Usability / demo value | 0.10 | 2 | 5 | 3 |
| Scalability / maintainability | 0.05 | 2 | 4 | 3 |
| **Weighted total** | **1.00** | **3.35** | **4.60** | **1.95** |

**Selected concept & justification:** Concept B. It gives two independent
factors (a secret pose and a behavioural biometric), keeps video on the
user's device, needs only a webcam, and can be built incrementally — the
non-neural verifiers (O1, O2) work in CP1 while the deep models (O3) are
added in CP2.

---

# WEEK 08 — Phase 3 · Requirements, Concept Selection & Design

### Header
| Field | Write |
|---|---|
| Week No. | 08 |
| Phase | Phase 3 — Requirements, Concept Selection & Design |
| Dates | `[dd/mm/yyyy – dd/mm/yyyy]` |
| Planned agenda / focus | Whole-system architecture (3 views), detailed design of O1 & O2, risk register, work-breakdown plan; set up the code repository. |

### Member-wise work
| Member | Tasks undertaken this week | Prog. % |
|---|---|---|
| 1. `[Name]` | Detailed design of O1 (gesture preprocessing, 115-feature extractor, template matcher) and O2 (trajectory preprocessing, DTW, behaviour features). | 100 |
| 2. `[Name]` | High-level architecture & component-interaction diagrams; MongoDB collection design; repository + folder structure (`client/`, `server/`, `ml-service/`). | 100 |
| 3. `[Name]` | Data-flow diagram (camera → landmarks → API → ML → decision); risk register; Gantt / work breakdown for weeks 9–15 and CP2. | 100 |

### Actionable items completed
- 3.5(a) high-level architecture, 3.5(b) data-flow, 3.5(c) component-interaction diagrams.
- 3.6 detailed design table for O1–O2.
- 3.7 risk register (8 risks) and 3.8 project plan.
- Git repository initialised with the agreed folder structure.

### Challenges faced & how addressed
- *Where to run the ML (Node.js vs Python)?* → separate Python FastAPI service; Express is the only public API and calls it with a shared service key.
- *Different hand sizes / camera distances* → design decision to normalise every hand into its own palm coordinate frame.

### Evidence produced
Diagrams on diary pp. 35–37; `Architecture/01_System_Architecture.md`; repository commit `[commit id]`.

### Action plan for next week
| Task | Expected outcome | Owner | Due |
|---|---|---|---|
| Implement gesture preprocessing + feature extraction | `static_gesture/preprocessing.py`, `features.py` | `[M1]` | `[date]` |
| Implement template matcher + enroll/verify | `static_gesture/verifier.py` | `[M1]` | `[date]` |
| In-browser hand tracking prototype | `CameraStage.jsx`, `handLandmarker.js` | `[M3]` | `[date]` |
| Write unit test plan (4.3) | Test IDs UT-01…UT-12 | `[M2]` | `[date]` |

### Points to raise with the guide
- Review of the three architecture views before implementation starts.
- Agreement on unit-test coverage expected for PDR.

---

## Sections to fill during Week 8

### 3.5(a) High-level architecture (diary p. 35) — draw this

```
 [User + Webcam]
       │ video (stays in browser)
       ▼
 ┌─────────────── Browser: React client ───────────────┐
 │ MediaPipe HandLandmarker → 21 landmarks / frame      │
 │ Gesture capture UI  ·  Air-signature capture UI      │
 └───────────────┬──────────────────────────────────────┘
                 │ HTTPS JSON (landmarks / trajectory only)
                 ▼
 ┌──────── Express API (Node.js) ────────┐      ┌────────────┐
 │ Registration · 2-step login state     │◄────►│  MongoDB   │
 │ Lockout · Rate limit · JWT · Audit    │      └────────────┘
 └───────────────┬───────────────────────┘
                 │ X-Service-Key
                 ▼
 ┌──────── ML service (Python FastAPI) ──────┐
 │ Step 1: gesture verifier                  │
 │ Step 2: air-signature verifier            │
 │ Models + calibration files                │
 └───────────────────────────────────────────┘
```
Legend: rectangles = deployable services; arrows = data flow; only
coordinates (never video) leave the browser.

### 3.5(b) Data-flow / block diagram (diary p. 36)

```
Camera frame → MediaPipe (21 landmarks)
  ├─ Step 1: 15 frames → clean & stability check → palm-frame normalisation
  │           → 115 features → template distance (+ embedding in CP2)
  │           → user-normalised score → threshold → MATCH / NO MATCH
  └─ Step 2: fingertip (t,x,y) per frame → trim idle → remove spikes
              → resample 128 points in time → normalise
              → DTW + 12 behaviour features (+ embedding in CP2)
              → fused score → threshold → ACCESS GRANTED / DENIED
```

### 3.5(c) Component-interaction diagram (diary p. 37)
Draw the login sequence:
`Client → API: login/start` → `API → Mongo: create LoginSession (stage=static)` →
`Client → API: static-gesture sample` → `API → ML: /static/verify` → `ML → API: result` →
`API → Mongo: log attempt, stage=dynamic` → `Client → API: air-signature sample` →
`API → ML: /dynamic/verify` → `API → Mongo: adapt template, delete session` → `API → Client: JWT`.
(Full version: `Architecture/01_System_Architecture.md`, section 3.)

### 3.6 Detailed design of O1–O2 (diary p. 38)

| Component | Description | Inputs | Outputs | Dependencies |
|---|---|---|---|---|
| Hand tracker (client) | MediaPipe HandLandmarker in VIDEO mode, 1 hand | Webcam frames | 21 × (x,y,z) + handedness | MediaPipe Tasks Vision |
| Gesture preprocessing (O1) | Parse frames, aspect-ratio fix, stability check, mirror left hands | 15 frames | Clean (F,21,3) array | NumPy |
| Gesture features (O1) | Palm-frame canonicalisation; angles, distances, abduction, orientation, bone ratios | Clean frames | 115-dim vector (median over frames) | Preprocessing |
| Gesture verifier (O1) | Enrollment consistency check; group-scaled template distance; wrong-hand & replay checks | Template + probe | Accept/reject, score | Features |
| Trajectory preprocessing (O2) | Clean, trim idle, MAD spike removal, resample 128 pts in time, normalise | (t,x,y,z) points | 128 × 2 trajectory | NumPy |
| Signature features (O2) | 9-channel sequence features; 12 behaviour statistics | Trajectory | Feature arrays | Preprocessing |
| DTW matcher (O2) | Sakoe-Chiba banded DTW, min distance to templates | Probe + templates | Distance | Preprocessing |
| Signature verifier (O2) | Personal normalisation, fusion, threshold, replay check | Template + probe | Accept/reject, score | DTW, features |

### 3.7 Risk register (diary p. 39)

| Risk ID | Description | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | Too little real data to train deep models | High | High | Synthetic pretraining; real data for evaluation only | `[M1]` |
| R2 | MediaPipe tracking jitter / spikes | High | Medium | MAD spike correction; median over frames | `[M1]` |
| R3 | Poor lighting / hand out of frame | Medium | Medium | "Hand detected" indicator; capture validation & retry | `[M3]` |
| R4 | Shoulder-surfer copies the gesture | Medium | High | Step 2 behavioural biometric | `[M1]` |
| R5 | Replay of captured landmark data | Low | High | Near-duplicate detection; rate limiting | `[M2]` |
| R6 | Slow verification on CPU | Medium | Medium | Small models; vectorised DTW; latency target < 1 s | `[M1]` |
| R7 | Biometric data privacy breach | Low | High | No video upload; templates server-only; delete-my-data | `[M2]` |
| R8 | Integration delays between 3 services | Medium | Medium | Agreed JSON API contract early; end-to-end test script | `[M2]` |

### 3.8 Project plan / work breakdown (diary p. 40)

| Phase / Task | Owner(s) | Start | End | Dependencies |
|---|---|---|---|---|
| O1 gesture preprocessing + features | `[M1]` | Wk 9 | Wk 9 | Design 3.6 |
| O1 verifier + unit tests | `[M1]`, `[M2]` | Wk 9 | Wk 10 | Features |
| Browser hand-tracking prototype | `[M3]` | Wk 9 | Wk 10 | — |
| O2 trajectory preprocessing + DTW | `[M1]` | Wk 10 | Wk 11 | Research dataset |
| O2 verifier + evaluation on research data | `[M1]`, `[M2]` | Wk 11 | Wk 12 | DTW |
| Initial integration O1 + O2 (5.1) | All | Wk 13 | Wk 14 | O1, O2 |
| Standards checklist + PDR preparation | All | Wk 14 | Wk 15 | — |
| CP2: embedding models (O3), MERN app (O4), evaluation (O5) | All | CP2 Wk 1 | CP2 Wk 13 | CP1 |

---

# WEEK 09 — Phase 4 · Implementation & Unit Testing (O1–O2)

### Header
| Field | Write |
|---|---|
| Week No. | 09 |
| Phase | Phase 4 — Implementation & Unit Testing (O1–O2) |
| Dates | `[dd/mm/yyyy – dd/mm/yyyy]` |
| Planned agenda / focus | Implement O1 (static gesture) preprocessing, feature extraction and template verifier; browser hand-tracking prototype; write the unit test plan. |

### Member-wise work
| Member | Tasks undertaken this week | Prog. % |
|---|---|---|
| 1. `[Name]` | Implemented `static_gesture/preprocessing.py` (frame parsing, aspect fix, stability check) and `features.py` (palm frame, 115 features); started `verifier.py`. | 70 |
| 2. `[Name]` | Wrote unit test plan (4.3); implemented first tests for feature size/invariance and capture validation; set up pytest. | 60 |
| 3. `[Name]` | Browser prototype: webcam + MediaPipe HandLandmarker drawing the 21-point skeleton live (`CameraStage.jsx`, `handLandmarker.js`). | 60 |

### Actionable items completed
- Gesture feature extractor working: extended finger ≈ 0–15° joint angle, curled ≈ 80–100°.
- Sanity check: same pose ≈ 0.6 distance units, different pose ≈ 3.0 → clearly separable.
- Live hand skeleton shown in the browser.

### Challenges faced & how addressed
- *Hand position changed between frames in our test data and triggered the stability check* → fixed the test-data generator to keep hand placement fixed within one capture; the check itself was correct.
- *Same gesture looked different when hand was tilted* → rotating landmarks into the palm's own coordinate frame removed the effect.

### Evidence produced
Commits `[commit ids]`; files `ml-service/airauth/static_gesture/*.py`, `client/src/components/CameraStage.jsx`; test cases UT-01 – UT-04.

### Action plan for next week
| Task | Expected outcome | Owner | Due |
|---|---|---|---|
| Finish O1 verifier (enroll/verify, wrong hand, replay) | All O1 unit tests pass | `[M1]` | `[date]` |
| Start O2 trajectory preprocessing | `dynamic_signature/preprocessing.py` | `[M1]` | `[date]` |
| Gesture capture UI with countdown | `StaticGestureCapture.jsx` | `[M3]` | `[date]` |
| Execute & record O1 tests (4.4) | Pass/fail table | `[M2]` | `[date]` |

### Points to raise with the guide
- Demo the live hand skeleton and feature values.
- Confirm target thresholds (EER ≤ 2 % for O1) are acceptable.

---

## Sections to start in Week 9

### 4.1 Implementation progress (diary p. 45)

| Task | Owner(s) | Start | End | % done | Dependencies |
|---|---|---|---|---|---|
| Gesture preprocessing | `[M1]` | Wk 9 | Wk 9 | 100 | — |
| Gesture feature extraction (115) | `[M1]` | Wk 9 | Wk 9 | 100 | Preprocessing |
| Gesture verifier (template matcher) | `[M1]` | Wk 9 | Wk 10 | 50 | Features |
| Browser hand tracking | `[M3]` | Wk 9 | Wk 10 | 60 | MediaPipe |
| Unit test suite (O1) | `[M2]` | Wk 9 | Wk 10 | 40 | Verifier |
| Trajectory preprocessing (O2) | `[M1]` | Wk 10 | Wk 11 | 0 | — |

### 4.3 Unit test plan (diary p. 52)
(These IDs match the real tests in `ml-service/tests/`.)

| Test-case ID | Description | Objective / module | Test type |
|---|---|---|---|
| UT-01 | Feature vector has 115 dims; pose vector 89 dims | O1 / features | Unit |
| UT-02 | Features unchanged when hand is moved/scaled | O1 / features | Unit |
| UT-03 | Genuine gesture accepted (≥ 4 of 5) | O1 / verifier | Unit |
| UT-04 | Different gesture rejected | O1 / verifier | Unit |
| UT-05 | Wrong hand rejected | O1 / verifier | Unit |
| UT-06 | Exact replay of stored sample rejected | O1 / verifier | Security |
| UT-07 | Enrollment with one different gesture flags that sample | O1 / verifier | Unit |
| UT-08 | Moving hand rejected ("unstable pose") | O1 / preprocessing | Unit |
| UT-09 | Too few frames rejected | O1 / preprocessing | Unit |
| UT-10 | Trajectory resampled to 128×2, normalised | O2 / preprocessing | Unit |
| UT-11 | Tracking spike detected and corrected | O2 / preprocessing | Unit |
| UT-12 | DTW(a,a)=0 and DTW symmetric | O2 / DTW | Unit |
| UT-13 | Genuine signature accepted, other writers rejected | O2 / verifier | Unit |
| UT-14 | Replayed signature rejected | O2 / verifier | Security |
| UT-15 | Too-short signature rejected | O2 / preprocessing | Unit |

### 4.4 Unit test execution (diary p. 53) — Week 9 entries only
Record only the tests you actually ran this week, e.g.:

| Test-case ID | Input | Expected output | Actual output | Pass/Fail |
|---|---|---|---|---|
| UT-01 | 10-frame synthetic gesture capture | 115 / 89 dims | 115 / 89 | Pass |
| UT-02 | Same frame ×1.7 and shifted | Identical pose vector | Identical (tol 1e-6) | Pass |
| UT-08 | 8 frames, hand re-placed each frame | Error `unstable_pose` | `unstable_pose` | Pass |
| UT-09 | Empty frame list | Error `too_few_frames` | `too_few_frames` | Pass |

(Fill UT-03 … UT-15 in weeks 10–12 as you run them.)

<!--
=============================================================================
FILE SUMMARY
-----------------------------------------------------------------------------
Weeks_07-09_Diary_Content.md gives ready-to-copy content for the KL University
Research Diary for weeks 7-9 of Capstone Project 1: the proposed objectives
O1-O5, each weekly progress log (header, member tasks, items completed,
challenges, evidence, next-week plan, points for the guide) and the phase
sections due in those weeks - requirements (3.1), constraints & standards
(3.2), candidate solutions (3.3), decision matrix (3.4), architecture views
(3.5), detailed design (3.6), risk register (3.7), project plan (3.8),
implementation progress (4.1) and the unit test plan / first executions
(4.3, 4.4). Placeholders in [ ] must be replaced with real team details.
=============================================================================
-->
