# AssetGuard

AssetGuard is a predictive and condition-monitoring development MVP for industrial equipment telemetry. It combines authenticated telemetry ingestion, adaptive statistical monitoring, operational alerts, optional AI enrichment, and human maintenance workflows in a local FastAPI, PostgreSQL, and Next.js application.

This repository is a development system, not a safety system or a production deployment.

## Architecture

```text
Physical Asset / Simulator
          -> Gateway
          -> Ingestion API
          -> PostgreSQL telemetry
          -> Condition Monitoring
          -> Operational Alerts
          -> Optional AI Enrichment
          -> Engineer / Technician workflow
```

`backend/scripts/simulate_gateway.py` represents the external industrial telemetry source during development. In a real installation, that boundary could instead receive data from a PLC gateway, OPC UA source, MQTT broker/client, SCADA or historian integration, vendor equipment API, or industrial database connector. The ingestion contract isolates these sources so the persistence, monitoring, alerting, AI, and workflow layers can remain largely unchanged.

The Next.js server stores the FastAPI access token in an HttpOnly cookie and proxies browser requests to the backend. FastAPI authentication and RBAC remain the authoritative security boundary.

## Local Setup

### Prerequisites

- Python 3.12 or newer
- PostgreSQL
- Node.js 20.9 or newer and npm

Create a PostgreSQL database and user for local development. Commands below use PowerShell from the project root; use equivalent activation commands on other platforms.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` with the local database URL and privately generated JWT and ingestion secrets. Add a Gemini API key only when AI analysis will be used. Never commit this file.

Apply the schema, create the first administrator interactively, and start FastAPI:

```powershell
python -m alembic upgrade head
python -m scripts.create_admin
python -m uvicorn app.main:app --reload
```

The admin command reads the password without terminal echo and stores an Argon2 hash. The API runs at `http://127.0.0.1:8000`; Swagger UI is at `http://127.0.0.1:8000/docs`.

### Frontend

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

`BACKEND_API_URL` is server-side configuration and defaults in the example to `http://127.0.0.1:8000`. Do not convert it to a `NEXT_PUBLIC_*` variable. Open `http://localhost:3000` and sign in with the administrator created above.

## Authentication And RBAC

All human-facing operational endpoints require a valid bearer token. The frontend applies the same permissions to improve navigation and control states, but FastAPI RBAC is the authoritative security boundary.

| Action | Admin | Engineer | Technician | Viewer |
| --- | --- | --- | --- | --- |
| Read assets, telemetry, assessments, alerts, AI, maintenance | Yes | Yes | Yes | Yes |
| Manage assets and sensors | Yes | No | No | No |
| Create individual readings through the user API | Yes | No | No | No |
| Run condition assessments and AI analysis | Yes | Yes | No | No |
| Create/edit/resolve alerts | Yes | Yes | No | No |
| Acknowledge alerts | Yes | Yes | Yes | No |
| Create/edit/cancel maintenance | Yes | Yes | No | No |
| Start/complete maintenance | Yes | Yes | Yes | No |
| Create, view, and update users | Yes | No | No | No |

Machine ingestion is separate from user RBAC and uses `X-AssetGuard-Ingestion-Key`. Access tokens are short-lived and stateless; logout removes the client session cookie, while token revocation and refresh tokens are outside this MVP.

## Telemetry Ingestion

`POST /api/ingestion/readings` accepts an API-key-authenticated batch of up to 500 readings. The ingestion key must match `INGESTION_API_KEY`. Each reading must reference a known sensor, use a timezone-aware timestamp, and contain a finite numeric value.

The unique `(sensor_id, recorded_at)` database key makes retries idempotent: duplicates are reported rather than inserted. Historical rows are retained, and timestamp ordering, rather than insertion order, determines a sensor's latest reading. `GET /api/ingestion/assets/{asset_code}/sensors` gives an authenticated gateway the sensor IDs and latest values needed to continue a stream.

Run the simulator from `backend` with the API running and `INGESTION_API_KEY` present in the simulator process environment:

```powershell
# Normal synthetic telemetry
python -m scripts.simulate_gateway --asset-code COMP-001 --interval 5 --cycles 12 --scenario normal --seed 42

# Stronger directional degradation for end-to-end QA
python -m scripts.simulate_gateway --asset-code COMP-001 --interval 5 --cycles 12 --scenario degrading --intensity 3 --seed 42

# Strong QA pattern
python -m scripts.simulate_gateway --asset-code COMP-001 --interval 5 --cycles 12 --scenario degrading --intensity 6 --seed 42
```

`--intensity` must be positive and scales only the degrading scenario's directional drift; ordinary random noise is unchanged. Its default of `1` preserves the original scenario. A seed makes generation reproducible from the same starting values.

All simulator values, baselines, noise, and drift are synthetic development telemetry. They are not OEM limits or real equipment specifications. Running the simulator writes persistent telemetry; it is never run automatically by setup or tests against the development database.

## Condition Monitoring

Each assessment evaluates recent readings per sensor against an adaptive statistical baseline:

1. The detector separates a recent observation window from up to 30 preceding baseline readings.
2. It uses the baseline median and the largest of MAD-derived scale, IQR-derived scale, and configured relative or absolute scale floors.
3. It measures the recent median's normalized displacement from that baseline.
4. It normalizes a linear trend over the latest readings against the same robust scale.
5. It calculates persistence as the proportion of recent points displaced in the same direction beyond the watch threshold.

The development defaults require 12 baseline readings plus a 5-reading recent window. Statuses are `insufficient_data`, `normal`, `watch`, and `anomalous`. The asset status is the most significant evaluable sensor status.

**NORMAL means statistically consistent with recent historical behaviour.** It does not mean mechanically healthy, safe, or within OEM limits.

Because the baseline adapts, a persistent changed operating state can eventually become part of the recent baseline. A future production detector may combine the adaptive baseline with a long-term known-good baseline and OEM or engineering operating envelopes. Those additions are not implemented here.

## Operational Alerting

```text
ConditionAssessment
  -> persistence policy
  -> operational Alert
  -> NotificationEvent
  -> optional AI enrichment
```

With default settings, `normal` and `watch` create no alert, the first `anomalous` assessment creates no alert, and two consecutive anomalous assessments create one moderate alert. A partial unique database index and service checks prevent duplicate active automatic alerts per asset.

Resolving an automatic alert starts the configured 60-minute cooldown. After cooldown, a fresh anomalous sequence must satisfy persistence again. Alerts never auto-resolve: acknowledgement and resolution remain human decisions. Automatic condition alerts describe statistical behavior and are not OEM safety alarms.

Each automatic alert records an internal `NotificationEvent` with pending delivery state. No external notification delivery is implemented.

## AI Analysis

Administrators and engineers can manually run Gemini analysis for an asset with enough telemetry. The service sends structured telemetry summaries, validates structured model output, stores the analysis, and can use the configured fallback model when appropriate.

Automatic enrichment of a newly created condition alert is controlled by `AUTO_AI_ESCALATION_ENABLED` and is `false` by default. Alert creation succeeds even when Gemini is disabled, unavailable, or fails; an attempted enrichment records `pending`, then `completed` or `failed` on the alert.

AI output is advisory and explanatory. It does not control machinery, declare equipment definitively safe or unsafe, automatically resolve alerts, schedule maintenance autonomously, or invent OEM limits.

## Maintenance Workflow

The normal workflow is `planned -> in_progress -> completed`. Administrators and engineers create, edit, and cancel records. Administrators, engineers, and technicians can start planned work and complete work in progress. Cancellation is allowed before completion and records the cancellation reason; completed records cannot be cancelled. Maintenance may optionally be linked to an alert for traceability.

## Database And Migrations

Major persistent entities are:

- `User`: identity, Argon2 password hash, role, and active state
- `Asset` and `Sensor`: equipment and measurement-point registry
- `SensorReading`: immutable timestamped telemetry history
- `ConditionAssessment`: deterministic per-asset statistical result and findings
- `Alert`: manual or condition-monitoring operational workflow
- `NotificationEvent`: internal alert notification outbox record
- `AIAnalysis`: stored Gemini result and deterministic telemetry context
- `MaintenanceRecord`: planned and completed human work history

Alembic migrations, in order:

1. `7ed5f8f61cfd` - initial domain schema
2. `c4a8f1d2e6b9` - users and authentication
3. `e8b7c6d5a4f3` - idempotent sensor readings
4. `f9c8d7e6b5a4` - condition assessments
5. `a1b2c3d4e5f6` - operational alert traceability and notification events (current head)

Use `python -m alembic upgrade head` to update a local database. Do not edit applied historical migrations to change the current schema.

## API Overview

- **Auth:** `/api/auth/login`, `/api/auth/me`, `/api/auth/logout`
- **Users:** `/api/users`
- **Assets:** `/api/assets`
- **Sensors:** `/api/assets/{asset_id}/sensors`, `/api/sensors/{sensor_id}`
- **Readings:** `/api/sensors/{sensor_id}/readings`, `/api/readings/{reading_id}`
- **Ingestion:** `/api/ingestion/readings`, `/api/ingestion/assets/{asset_code}/sensors`
- **Condition assessments:** `/api/assets/{asset_id}/condition-assessments`, `/api/condition-assessments/{assessment_id}`
- **Alerts:** `/api/assets/{asset_id}/alerts`, `/api/alerts/{alert_id}` and workflow actions
- **Maintenance:** `/api/assets/{asset_id}/maintenance-records`, `/api/maintenance-records/{record_id}` and workflow actions
- **AI analysis:** `/api/assets/{asset_id}/ai-analyses`, `/api/ai-analyses/{analysis_id}`

See `http://127.0.0.1:8000/docs` for request schemas, query parameters, response models, and interactive API calls while FastAPI is running.

## Current Development Data

The local PostgreSQL database is intentionally not reset by repository setup or this handover. It may contain `COMP-001`, four synthetic sensors, accumulated simulator telemetry, condition assessments, and manually or automatically generated alert, AI, and maintenance workflow records. Exact row counts vary during testing.

## Validation

Run backend checks from `backend` with the virtual environment active:

```powershell
python -m pytest
python -c "from app.main import app; print(app.title)"
python -m alembic current
python -m alembic check
```

Run frontend and repository checks:

```powershell
cd frontend
npm run lint
npx tsc --noEmit
npm run build
cd ..
git diff --check
```

## Current Limitations And Future Extensions

- A simulator stands in for a real PLC, historian, or industrial gateway.
- No OPC UA or MQTT connector is implemented.
- Raw high-frequency vibration waveform processing is not implemented.
- Monitoring uses an adaptive recent baseline only; there is no known-good baseline or OEM operating envelope.
- Notification events are internal only; there is no email, SMS, or Teams delivery.
- No production deployment, production-grade observability, or backup infrastructure is included.
