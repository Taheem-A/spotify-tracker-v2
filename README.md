# Personal Spotify Listening Tracker V2

A local-first Spotify listening-history, reconciliation, analytics, and visualization application built against the included **Program Specification v1.1**.

## What is included

- Python / FastAPI backend
- SQLite database with WAL, foreign keys, schema migration bootstrap and canonical-play model
- Raw Spotify Extended Streaming History preservation
- Safe repeated imports and exact-event deduplication
- Normalization and reconciliation audit trail
- Field-level provenance
- Spotify OAuth Authorization Code + PKCE
- Current playback / Now Playing API
- Isolated `ENABLE_DERIVED_LISTENING_METRICS` feature gate, default **false**
- JSON / CSV canonical-history exports
- Verified SQLite backups and database diagnostics
- React + TypeScript + Vite frontend
- Dark/light semantic design tokens matching the approved UI direction
- Home, History, Tracks, Artists, Albums, Track/Artist/Album detail, Discover, Compare, Calendar, Data/Imports and Settings screens
- Tests for import idempotency, overlapping exports, repeated same-track plays, unknown-vs-zero behavior, analytics, and the derived-metrics gate

## 1. Requirements

- Python 3.11+
- Node.js 20+ / npm
- A Spotify developer application only if you want live Spotify integration. Extended Streaming History imports work without Spotify API authentication.

## 2. Backend setup

From the project root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/run_backend.py
```

Backend: `http://127.0.0.1:8765`
API documentation: `http://127.0.0.1:8765/docs`

The SQLite database is created automatically at `data/tracker.db`.

## 3. Frontend setup

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## 4. Spotify OAuth setup

Create an app in Spotify's developer dashboard and configure this redirect URI:

```text
http://127.0.0.1:8765/api/auth/callback
```

Then set the client ID before starting the backend:

```powershell
$env:SPOTIFY_CLIENT_ID="your-client-id"
```

No client secret is required by the app; it uses PKCE.

## 5. Import Extended Streaming History

Open **Data → Import Spotify data** and choose either:

- a Spotify Extended Streaming History `.json` file, or
- a `.zip` containing the JSON files.

The flow is **Select → Validate → Preview → Import → Result**. Re-importing the same or overlapping history does not create duplicate canonical plays.

## 6. Derived listening metrics feature gate

Default:

```text
ENABLE_DERIVED_LISTENING_METRICS=false
```

To explicitly start the backend with the gated subsystem enabled:

```powershell
$env:ENABLE_DERIVED_LISTENING_METRICS="true"
python scripts/run_backend.py
```

The setting exists as an engineering/compliance boundary. Enabling it does not itself establish compliance with Spotify's Developer Policy. With the flag off, Extended History analytics and direct Now Playing display remain functional, while live observations are not silently turned into derived listening history.

## 7. Tests

```powershell
pytest -q
```

## Important data model rule

Raw source evidence is not destructively replaced. The application maintains the conceptual path:

```text
RAW → NORMALIZED → RECONCILIATION → CANONICAL → ANALYTICS → UI
```

`NULL` / unknown is never silently treated as zero.

## Specification

The exact specification used for the project is included at:

`docs/program-specification-v1.1.pdf`
