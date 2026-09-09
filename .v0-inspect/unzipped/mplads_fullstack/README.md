# MPLADS Risk Screening — Full Stack (SIH26102)

A real, ready-to-run application: **FastAPI backend + SQLite database + React
frontend**, built on the same anomaly-detection pipeline as the MVP, with a
distinctive "audit case-file" UI instead of a generic dashboard template.

```
backend/    FastAPI API + SQLite database + the ML/anomaly pipeline
frontend/   React + Tailwind UI (Vite dev server)
```

## Quick start (two terminals)

### Terminal 1 — Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
First run automatically generates realistic sample data (with labelled test
anomalies), runs the full detection pipeline, and stores everything in
`backend/data/mplads.db`. Every later run just reads from that database —
instant startup, and any investigator feedback you've given persists.

Check it's alive: open http://localhost:8000/api/health — you should see
`{"status": "ok", ...}`. Interactive API docs: http://localhost:8000/docs

### Terminal 2 — Frontend
```bash
cd frontend
npm install
npm run dev
```
Open the URL it prints (usually http://localhost:5173). The dev server
proxies `/api/*` to the backend automatically (see `vite.config.js`), so no
CORS headaches.

## What you get

- **Case Register** (`/`) — every work, filterable by state/sector/search/
  minimum risk score, sorted by risk. Click any row to open its case file.
- **Case file** (`/project/:workId`) — the risk "stamp", plain-English
  evidence for why it was flagged, a signal-by-signal breakdown, and
  **Confirm / False Positive** buttons an investigator can click.
- **Repeat Patterns** (`/entities`) — aggregates risk by MP or implementing
  agency, surfacing systemic patterns across many works, not just one-off
  flags.
- **How Scoring Works** (`/about`) — plain-language explanation of the four
  signals, plus the *live* current weights, which shift slightly every time
  someone clicks Confirm/False Positive on the Case file page. Refresh after
  giving a few verdicts and watch the weights move.

## Switching to real MPLADS data

1. Get a real work-level CSV (see the MVP README for sources: MoSPI's
   eSAKSHI portal, Dataful, data.gov.in).
2. Save it as `backend/data/raw_mplads_sample.csv`, replacing the generated one.
3. Open `backend/pipeline/data_cleaning.py` and fill in `COLUMN_MAP` if the
   real column names differ from the ones this pipeline expects.
4. Delete `backend/data/mplads.db` and restart the backend — it will re-run
   the pipeline against your real file and rebuild the database.

## Architecture at a glance

```
raw CSV → data_cleaning → anomaly_detection (cost/delay/duplicate/confidence)
        → risk_engine (weighted score + reasons) → SQLite
        → FastAPI REST API → React dashboard
                                   ↑
                    investigator feedback nudges weights,
                    which recompute every score in the database
```

## Notes on production-readiness

This is genuinely runnable and demoable, not a mockup — but before treating
it as production software for real government use, you'd still want to add:
authentication (who's allowed to give feedback), an audit log of who
confirmed/rejected what, a proper Postgres database instead of SQLite once
more than one person writes at a time, and HTTPS/deployment config. The
architecture above doesn't need to change for any of that — it's a matter of
adding layers, not rebuilding.
