
# RazControl AI

RazControl AI is a deterministic financial-control pipeline with an evidence-grounded investigation stage and a static operations dashboard. It processes persisted transaction and bank data through:

- **RazRecon**: one-to-one bank-to-GL reconciliation with matched, review, and unmatched outcomes.
- **RazGuard**: deterministic control rules for materiality, duplicates, dates, data quality, and reconciliation exceptions.
- **RazDetect**: explainable historical IQR anomaly detection with explicit control and reconciliation score modifiers.
- **RazInvestigate**: evidence-only investigations that cite persisted source records and do not assert unsourced causes.
- **RazReport**: read-only risk summaries, finding details, transaction risk views, and CSV export.
- **Frontend**: the `frontend/` static dashboard for live metrics, findings, actions, filters, and reports.

## Architecture

FastAPI exposes the agent routes in `backend/app/api`. SQLAlchemy models persist source data and agent results in PostgreSQL. Each service commits its own successful stage; the pipeline reports partial failures without hiding earlier results. The default investigation provider is `evidence_only`.

## Local setup

1. Create a virtual environment in `backend/.venv` and install dependencies:

	```powershell
	cd backend
	.\.venv\Scripts\python.exe -m pip install -r requirements.txt
	```

2. Start PostgreSQL. The default local URL is `postgresql://razcontrol:razcontrol@localhost:5432/razcontrol`; use environment variables for non-development credentials.

3. Start the API from `backend`:

	```powershell
	.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
	```

4. Start the dashboard in another terminal:

	```powershell
	python -m http.server 5173 -d frontend
	```

	Open `http://localhost:5173`.

The application reads process environment variables first. For local settings, copy `.env.example` to an ignored `.env` in the directory used to start the API, then replace the placeholder password. Never commit `.env`.

## Docker

Copy `.env.example` to `.env`, set `POSTGRES_PASSWORD` to a real secret, and run:

```powershell
docker compose up --build
```

Compose starts PostgreSQL, the FastAPI backend on port 8000, the nginx frontend on port 5173, and Redis for future workers. The backend waits for PostgreSQL health before starting. Database schema creation is currently performed by SQLAlchemy startup; the SQL files in `backend/migrations/` document incremental integrity changes and should be applied through an explicit migration process before changing an existing production database.

## Tests

Run the complete suite with the repository virtual environment:

```powershell
$env:PYTHONPATH=(Resolve-Path backend).Path
cd backend
Get-ChildItem tests -Filter 'test_*.py' | ForEach-Object { .\.venv\Scripts\python.exe $_.FullName }
\.venv\Scripts\python.exe -m compileall -q app tests
```

The repository currently has backend `unittest` coverage and no Node package or frontend test runner. The dashboard can be smoke-tested by serving `frontend/` and checking the live API-backed routes.

## API groups

- `/reconciliation`: run and list reconciliation results.
- `/guard`: scan controls, list findings, summaries, and update finding status.
- `/detect`: run detection, list filtered anomalies, and view summaries.
- `/investigations`: run, list, inspect evidence, and update investigations.
- `/reports`: overall/summary reports, transaction risk, finding lookup, and CSV export.
- `/pipeline/run`: execute Recon, Guard, Detect, optional Investigate, and Report in order.

## Environment variables

`DATABASE_URL`, `DEBUG`, `CORS_ORIGINS`, `ANOMALY_MIN_HISTORY`, `ANOMALY_IQR_MULTIPLIER`, `ANOMALY_MIN_RISK_SCORE`, `ANOMALY_USE_ML`, `INVESTIGATION_PROVIDER`, and `PIPELINE_MAX_INVESTIGATIONS` are supported by the backend. `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` configure the Compose database.
