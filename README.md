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
- Tests for import idempotency, overlapping exports, repeated same-track plays, unknown-vs-zero behavior, analytics, OAuth state validation, and the derived-metrics gate

## 1. Requirements

- **Python 3.11, 3.12, or 3.13**. Python 3.14 is not currently supported by the pinned dependency set.
- **Node.js 20+ / npm**
- A Spotify developer application only if you want live Spotify integration. Extended Streaming History imports work without Spotify API authentication.

The preferred local Python version is declared in `.python-version`.

## 2. Recommended Windows startup

From the project root, run:

```powershell
.\start.ps1
```

Or double-click:

```text
start.bat
```

The startup script:

1. finds a supported Python installation;
2. creates `.venv` if necessary;
3. installs the pinned backend dependencies;
4. creates `.env` from `.env.example` on first run;
5. starts the FastAPI backend in a separate PowerShell window;
6. installs frontend dependencies when needed;
7. starts the Vite frontend.

Backend: `http://127.0.0.1:8765`

API documentation: `http://127.0.0.1:8765/docs`

Frontend: `http://127.0.0.1:5173`

The SQLite database is created automatically at `data/tracker.db`.

If an old `.venv` was created with unsupported Python, delete `.venv` and run `start.ps1` again.

## 3. Manual backend setup

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/run_backend.py
```

The launcher explicitly adds the repository root to the Python import path, so `app.main` resolves correctly on Windows even when launched from `scripts/`.

## 4. Manual frontend setup

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## 5. Local configuration

Copy `.env.example` to `.env` or let `start.ps1` create it automatically.

```dotenv
SPOTIFY_CLIENT_ID=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8765/api/auth/callback
ENABLE_DERIVED_LISTENING_METRICS=false
```

`.env` is ignored by Git and must never be committed.

Environment variables override values from `config/settings.toml` where supported.

## 6. Spotify OAuth setup

Create an app in Spotify's developer dashboard and configure this redirect URI exactly:

```text
http://127.0.0.1:8765/api/auth/callback
```

Then put the client ID in `.env`:

```dotenv
SPOTIFY_CLIENT_ID=your-client-id
```

No client secret is required by the app; it uses Authorization Code + PKCE. OAuth callbacks validate the generated `state` value before exchanging the authorization code.

## 7. Import Extended Streaming History

Open **Data → Import Spotify data** and choose either:

- a Spotify Extended Streaming History `.json` file, or
- a `.zip` containing the JSON files.

The flow is **Select → Validate → Preview → Import → Result**. Re-importing the same or overlapping history does not create duplicate canonical plays.

## 8. Derived listening metrics feature gate

Default:

```text
ENABLE_DERIVED_LISTENING_METRICS=false
```

To explicitly start the backend with the gated subsystem enabled, set the value in `.env` or in the current PowerShell environment.

The setting exists as an engineering/compliance boundary. Enabling it does not itself establish compliance with Spotify's Developer Policy. With the flag off, Extended History analytics and direct Now Playing display remain functional, while live observations are not silently turned into derived listening history.

## 9. Tests

```powershell
python -m pytest -q
```

GitHub Actions also runs the backend suite on Python 3.11, 3.12, and 3.13 and builds the frontend with Node.js 20 for pull requests and pushes to `main`.

## Important data model rule

Raw source evidence is not destructively replaced. The application maintains the conceptual path:

```text
RAW → NORMALIZED → RECONCILIATION → CANONICAL → ANALYTICS → UI
```

`NULL` / unknown is never silently treated as zero.

## Specification

The exact specification used for the project is included at:

`docs/program-specification-v1.1.pdf`
