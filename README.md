# PedesPi — Pedestrian Detection System (Full-Stack Scaffold)

Reference architecture for the CS308 Pedestrian Detection System (YOLO-based
object detection) described in the project write-up. This is a **production-shaped
scaffold**: the API, database schema, service boundaries, and frontend are all
real and internally consistent, but the YOLO inference call and live camera
ingestion are stubbed out (`app/ml/yolo_wrapper.py`) since this environment has
no GPU, no camera hardware, and no network access to model weight servers.
Everything else — routing, auth, persistence, business logic, websocket
fan-out, dashboard UI — is written the way it would ship.

## Why it's structured this way

The write-up's functional requirements (FR-01 … FR-13) map directly onto the
service layer so that each FR is traceable to one module:

| FR(s) | Component |
|---|---|
| FR-01, FR-02 | `services/video_capture.py`, `services/frame_preprocessor.py` |
| FR-03, FR-04 | `services/yolo_inference.py` + `ml/yolo_wrapper.py` |
| FR-05 | `services/tracker.py` |
| FR-06, FR-07 | `services/risk_classifier.py` (implements the Section 9 decision tree) |
| FR-08 | `services/alert_service.py` + `api/v1/endpoints/ws.py` |
| FR-09 | `models/detection_event.py`, `models/alert.py` |
| FR-10 | `api/v1/endpoints/dashboard.py`, frontend `pages/Dashboard.jsx` |
| FR-11 | `api/v1/endpoints/zones.py`, `zones` table |
| FR-12 | `api/v1/endpoints/users.py`, RBAC in `core/security.py` |
| FR-13 | `api/v1/endpoints/models.py`, `models/model_version.py` |

NFR-06 (RBAC + encryption) and NFR-07 (Ghana Data Protection Act, 2012 — Act
843) are addressed structurally: role checks live in `api/deps.py`, and
`detection_events` never stores raw imagery — only bounding-box coordinates,
a confidence score, and a reference to an (optionally encrypted, short-retention)
clip stored outside the relational DB, per NFR-07's data-minimisation intent.

## Layout

```
pedestrian-detection-system/
├── backend/            FastAPI service (Python 3.11)
│   ├── app/
│   │   ├── main.py             FastAPI app factory, router mount, startup hooks
│   │   ├── core/                config, JWT auth, RBAC, logging
│   │   ├── db/                  SQLAlchemy engine/session, declarative base
│   │   ├── models/               ORM models — one file per table
│   │   ├── schemas/              Pydantic request/response contracts
│   │   ├── api/v1/endpoints/     one router per resource (see table above)
│   │   ├── services/             the detection pipeline, decoupled from HTTP
│   │   └── ml/                   model loading / inference boundary (stubbed)
│   ├── alembic/                  migration scaffold (0001 = initial schema)
│   └── requirements.txt
├── frontend/            React + Vite admin/ops dashboard
│   └── src/pages/        Login, Dashboard, LiveFeed, Alerts, Zones, Users
├── db/schema.sql         plain-SQL mirror of the Alembic migration, for review
├── docker-compose.yml    api + postgres + redis + frontend
└── .env.example
```

## Data flow (matches Section 9's decision tree)

```
Camera/CCTV/File  →  video_capture.py  →  frame_preprocessor.py
      →  yolo_inference.py (ml/yolo_wrapper.py)  →  confidence filter (≥0.5)
      →  tracker.py (assigns/maintains track_id)
      →  risk_classifier.py:
             not in risk zone           → log only
             in zone, beyond safe dist  → log only
             in zone, within safe dist:
                 closing speed > 2 m/s  → CRITICAL  → alert_service.py → WS push + FR-08 alert
                 closing speed ≤ 2 m/s  → CAUTION   → alert_service.py → WS push
      →  detection_events / alerts tables  →  dashboard API  →  frontend
```

`pipeline_orchestrator.py` wires these steps together as an async generator so
it can be driven either by a background worker (real deployment, reading from
an RTSP camera) or by a test harness feeding in recorded frames.

## Running it (not executed in this environment)

```bash
cp .env.example .env
docker compose up --build
# API:      http://localhost:8000/docs   (OpenAPI/Swagger)
# Frontend: http://localhost:5173
```

Nothing here was run end-to-end in this sandbox — there's no GPU, no camera
feed, and package installation from PyPI/npm at this scope is out of budget
for a scaffold review. The FastAPI app itself follows standard patterns
(dependency-injected DB sessions, Pydantic v2 schemas, Alembic migrations) so
`docker compose up` on a real machine with the `.env` filled in should bring
it up as-is, modulo actually supplying YOLO weights.

## What's stubbed vs. real

- **Real**: routing, request/response schemas, auth + RBAC, SQLAlchemy models
  and relationships, the risk-classification decision tree, websocket alert
  fan-out, the React dashboard and its API client, DB schema/migrations.
- **Stubbed** (clearly marked `# STUB` in code): the actual `ultralytics`
  YOLO forward pass, the tracker's association algorithm (a real deployment
  would use ByteTrack/DeepSORT — a minimal IoU-matching stand-in is included
  so the interface and data shape are correct), and RTSP frame reading.
