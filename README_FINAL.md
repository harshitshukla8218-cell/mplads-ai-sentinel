# MPLADS AI SENTINEL — SIH Final Build

This build combines the v0 investigation UI with the FastAPI screening backend and a supplied MPLADS work-record development snapshot.

## Current data
- Source: MPLADS work-record development snapshot supplied for development.
- Snapshot coverage: records dated through 2024-03-04.
- 53,512 unique usable records after cleaning/deduplication.
- The supplied snapshot does not contain expenditure, physical-progress, expected-completion, district, or coordinates. Sentinel reports those as unavailable and does not fabricate them.

## Run backend
```bash
cd .v0-inspect/unzipped/mplads_fullstack/backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

## Run frontend
```bash
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

On Windows PowerShell:
```powershell
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Updating data later
Use the Data Ingestion module to upload a newer authorized/authoritative CSV. The backend versions snapshots, detects new/changed fields by stable work ID, and re-runs screening. The source freshness endpoint makes stale-source state explicit instead of pretending the data is live.

## Important guardrail
Risk is an investigation-prioritization signal, not a finding of fraud. Missing source fields are not treated as zero-risk evidence.
