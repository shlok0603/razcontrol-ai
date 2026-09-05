# RazControl AI

> **AI-powered financial-control, reconciliation, anomaly detection, investigation, and risk reporting platform.**

RazControl AI is a deterministic financial-control pipeline with an evidence-grounded investigation stage and a static operations dashboard. It processes persisted transaction and bank data through:

- **RazRecon**: one-to-one bank-to-GL reconciliation with matched, review, and unmatched outcomes.
- **RazGuard**: deterministic control rules for materiality, duplicates, dates, data quality, and reconciliation exceptions.
- **RazDetect**: explainable historical IQR anomaly detection with explicit control and reconciliation score modifiers.
- **RazInvestigate**: evidence-only investigations that cite persisted source records and do not assert unsourced causes.
- **RazReport**: read-only risk summaries, finding details, transaction risk views, and CSV export.
- **Frontend**: the `frontend/` static dashboard for live metrics, findings, actions, filters, and reports.

---

## 1. Problem Statement

Financial operations teams process large volumes of transactions across bank systems, general ledgers, control systems, and reporting workflows.

This creates several challenges:

- Bank transactions may not match their corresponding GL transactions.
- Duplicate or suspicious transactions can be difficult to identify.
- High-value transactions may require manual review.
- Weekend or unusual-date transactions may require additional scrutiny.
- Data-quality problems can affect downstream financial controls.
- Statistical anomalies may be difficult to identify using simple rules.
- Analysts may need to investigate findings across multiple systems.
- Evidence supporting a finding can be difficult to trace.
- Manual investigation is time-consuming.
- Risk information is often distributed across separate reports.
- Operational teams need a consolidated view of financial risk.

A financial-control system therefore needs to provide:

```text
Reconciliation
      +
Deterministic Controls
      +
Anomaly Detection
      +
Evidence-Based Investigation
      +
Risk Reporting
      +
Operational Visibility
```

---

## 2. Solution

RazControl AI addresses this problem through an end-to-end financial-control workflow that connects transaction processing, reconciliation, control evaluation, anomaly detection, investigation, and reporting.

```mermaid
flowchart TD
    A[Financial Data] --> B[(PostgreSQL)]
    B --> C[RazRecon]
    C --> D[RazGuard]
    D --> E[RazDetect]
    E --> F[RazInvestigate]
    F --> G[RazReport]
    G --> H[FastAPI]
    H --> I[Operations Dashboard]

    C --> B
    D --> B
    E --> B
    F --> B
    G --> B
```

The core workflow is:

**Data → Reconcile → Control → Detect → Investigate → Report → Dashboard**

The key design principle is:

> **Deterministic controls determine financial findings, while evidence-grounded investigation explains those findings using persisted evidence.**

---

## 3. Key Features

### 3.1 Bank-to-GL Reconciliation

RazRecon performs one-to-one reconciliation between bank transactions and GL transactions.

Each bank transaction receives one of three outcomes:

```text
MATCHED
REVIEW
UNMATCHED
```

The current matching weights are:

```text
Amount       → 50%
Date         → 20%
Description  → 30%
```

Confirmed matches reserve their GL transaction IDs to maintain one-to-one matching.

### 3.2 Deterministic Financial Controls

RazGuard applies deterministic financial-control rules covering:

```text
HIGH_VALUE_TRANSACTION
WEEKEND_TRANSACTION
RECONCILIATION_EXCEPTION
DUPLICATE_TRANSACTION
DATA_QUALITY
```

### 3.3 Explainable Anomaly Detection

RazDetect uses historical IQR-based anomaly detection and applies explicit control and reconciliation score modifiers.

### 3.4 Evidence-Grounded Investigation

RazInvestigate creates evidence-only investigations from persisted source records.

The default investigation provider is:

```text
evidence_only
```

The investigation stage does not assert unsupported causes and does not override deterministic control decisions.

### 3.5 Risk Reporting

RazReport provides:

- Overall risk summaries
- Finding details
- Transaction risk views
- Reconciliation summaries
- Control summaries
- Anomaly summaries
- Investigation summaries
- CSV export

### 3.6 Operations Dashboard

The frontend provides:

- Overview
- Reconciliation
- Controls
- Anomalies
- Investigations
- Reports
- Live API-backed metrics
- Filtering
- Finding status actions
- Investigation status actions
- CSV export
- Loading, error, and empty states

---

# 4. Architecture

FastAPI exposes the agent routes in `backend/app/api`. SQLAlchemy models persist source data and agent results in PostgreSQL. Each service commits its own successful stage; the pipeline reports partial failures without hiding earlier results. The default investigation provider is `evidence_only`.

### High-Level Architecture

```mermaid
flowchart TB
    A[GL Transactions] --> DB[(PostgreSQL)]
    B[Bank Transactions] --> DB

    DB --> R[RazRecon]
    R --> G[RazGuard]
    G --> D[RazDetect]

    D --> I[RazInvestigate]
    G --> I
    R --> I

    I --> RP[RazReport]
    R --> RP
    G --> RP
    D --> RP

    RP --> API[FastAPI REST API]
    API --> UI[Static Operations Dashboard]

    UI --> U1[Overview]
    UI --> U2[Reconciliation]
    UI --> U3[Controls]
    UI --> U4[Anomalies]
    UI --> U5[Investigations]
    UI --> U6[Reports]
```

### End-to-End Pipeline

```mermaid
flowchart LR
    A[Financial Data] --> B[RazRecon]
    B -->|MATCHED / REVIEW / UNMATCHED| C[RazGuard]
    C -->|Control Findings| D[RazDetect]
    D -->|Anomalies + Risk| E[RazInvestigate]
    C --> E
    B --> E
    E --> F[RazReport]
    B --> F
    C --> F
    D --> F
    F --> G[FastAPI]
    G --> H[Frontend Dashboard]
```

### Complete Processing Flow

```mermaid
flowchart TD
    START([Financial Data])

    START --> DB[(PostgreSQL)]
    DB --> R[RazRecon]

    R --> R1{Reconciliation Result}
    R1 -->|MATCHED| G[RazGuard]
    R1 -->|REVIEW| G
    R1 -->|UNMATCHED| G

    G --> G1[Deterministic Control Rules]
    G1 --> G2[Persist Control Findings]

    G2 --> D[RazDetect]
    D --> D1[Historical IQR Analysis]
    D1 --> D2[Risk Scoring]
    D2 --> D3[Persist Anomalies]

    D3 --> I[RazInvestigate]
    G2 --> I
    R --> I

    I --> I1[Retrieve Persisted Evidence]
    I1 --> I2[Evidence-Grounded Investigation]
    I2 --> I3[Persist Investigation]

    I3 --> RP[RazReport]
    R --> RP
    G2 --> RP
    D3 --> RP

    RP --> API[FastAPI]
    API --> UI[Operations Dashboard]
```

---

# 5. Module Architecture

## RazRecon

```mermaid
flowchart TD
    A[Bank Transaction] --> B[Retrieve GL Candidates]
    B --> C[Amount Similarity]
    B --> D[Date Similarity]
    B --> E[Description Similarity]

    C --> F[Weighted Match Score]
    D --> F
    E --> F

    F --> G{Confidence}
    G -->|High| H[MATCHED]
    G -->|Medium| I[REVIEW]
    G -->|Low / No Candidate| J[UNMATCHED]

    H --> K[Reserve GL Transaction]
    I --> L[Persist Review Candidate]
    J --> M[Persist Without GL Match]

    K --> N[(PostgreSQL)]
    L --> N
    M --> N
```

Matching weights:

```python
AMOUNT_WEIGHT = 0.50
DATE_WEIGHT = 0.20
DESCRIPTION_WEIGHT = 0.30
```

Only confirmed `MATCHED` results reserve GL transaction IDs. `REVIEW` retains its candidate information without reserving the GL transaction, while `UNMATCHED` is persisted without a GL match.

---

## RazGuard

```mermaid
flowchart TD
    A[Persisted Financial Data] --> B[Control Engine]

    B --> C{High Value?}
    C -->|Yes| D[HIGH_VALUE_TRANSACTION]
    C -->|No| E[Continue]

    E --> F{Weekend / Date Rule?}
    F -->|Yes| G[WEEKEND_TRANSACTION]
    F -->|No| H[Continue]

    H --> I{Duplicate / Data Quality?}
    I -->|Yes| J[Control Finding]
    I -->|No| K[Continue]

    K --> L{Reconciliation Exception?}
    L -->|Yes| M[RECONCILIATION_EXCEPTION]
    L -->|No| N[No Finding]

    D --> O[Persist Finding]
    G --> O
    J --> O
    M --> O

    O --> P[(PostgreSQL)]
```

RazGuard findings use deterministic fingerprints to support repeatable, idempotent scanning.

---

## RazDetect

```mermaid
flowchart TD
    A[Historical Transactions] --> B[Build Historical Population]
    B --> C[Calculate Q1]
    B --> D[Calculate Q3]
    C --> E[IQR]
    D --> E
    E --> F[Historical Bounds]
    F --> G[Evaluate Transaction]
    G --> H{Outside Expected Range?}
    H -->|No| I[Normal]
    H -->|Yes| J[Potential Anomaly]
    J --> K[Calculate Risk Score]
    K --> L[Control Modifier]
    L --> M[Reconciliation Modifier]
    M --> N[Persist Anomaly]
```

IQR:

```text
Q1 = First Quartile
Q3 = Third Quartile
IQR = Q3 - Q1
```

---

## RazInvestigate

```mermaid
flowchart TD
    A[High-Risk Finding] --> B[Retrieve Persisted Evidence]
    B --> C{Evidence Available?}
    C -->|No| D[Insufficient Evidence]
    C -->|Yes| E[Build Evidence Context]
    E --> F[Evidence-Only Provider]
    F --> G[Validate Output]
    G --> H[Persist Investigation]
    D --> H
```

Investigation principles:

```text
Persisted Evidence
        ↓
Evidence Context
        ↓
Investigation
        ↓
Evidence References
        ↓
Auditable Result
```

---

## RazReport

RazReport is read-only.

```mermaid
flowchart TD
    DB[(PostgreSQL)] --> A[Transactions]
    DB --> B[Reconciliation]
    DB --> C[Control Findings]
    DB --> D[Anomalies]
    DB --> E[Investigations]

    A --> F[Report Aggregation]
    B --> F
    C --> F
    D --> F
    E --> F

    F --> G[Summary]
    F --> H[Overall Risk]
    F --> I[Transaction Risk]
    F --> J[Finding Details]
    F --> K[CSV Export]
```

---

# 6. Frontend Architecture

The frontend is a static dashboard located in:

```text
frontend/
```

It communicates with FastAPI through REST APIs.

```mermaid
flowchart LR
    UI[RazControl Dashboard]

    UI --> O[Overview]
    UI --> R[Reconciliation]
    UI --> C[Controls]
    UI --> A[Anomalies]
    UI --> I[Investigations]
    UI --> RP[Reports]

    O --> API[FastAPI]
    R --> API
    C --> API
    A --> API
    I --> API
    RP --> API

    API --> DB[(PostgreSQL)]
```

Dashboard pages:

| Page | Purpose |
|---|---|
| Overview | Overall financial-control health |
| Reconciliation | Bank-to-GL reconciliation results |
| Controls | Persisted control violations |
| Anomalies | Statistical anomalies |
| Investigations | Evidence-grounded investigations |
| Reports | Consolidated risk reporting and CSV export |

---

# 7. Database Architecture

PostgreSQL stores source financial data and generated results.

```mermaid
erDiagram
    TRANSACTION {
        string transaction_id
        date transaction_date
        decimal amount
        string description
        string vendor
        string account
    }

    BANK_TRANSACTION {
        string bank_transaction_id
        date transaction_date
        decimal amount
        string description
        string reconciliation_status
    }

    RECONCILIATION_MATCH {
        string match_id
        string bank_transaction_id
        string transaction_id
        string status
        decimal confidence
    }

    CONTROL_FINDING {
        string finding_id
        string fingerprint
        string control_type
        string severity
        string status
    }

    ANOMALY {
        string anomaly_id
        string fingerprint
        string anomaly_type
        decimal risk_score
        string severity
    }

    INVESTIGATION {
        string investigation_id
        string fingerprint
        string target_type
        string target_id
        string status
    }

    TRANSACTION ||--o{ RECONCILIATION_MATCH : matched_to
    BANK_TRANSACTION ||--o{ RECONCILIATION_MATCH : produces
    TRANSACTION ||--o{ CONTROL_FINDING : triggers
    BANK_TRANSACTION ||--o{ CONTROL_FINDING : triggers
    TRANSACTION ||--o{ ANOMALY : produces
    CONTROL_FINDING ||--o{ INVESTIGATION : investigated
    ANOMALY ||--o{ INVESTIGATION : investigated
```

---

# 8. Risk Model

RazControl combines information from multiple stages:

```text
Transaction
    │
    ├── Reconciliation Result
    │
    ├── Control Findings
    │
    ├── Anomaly Detection
    │
    └── Investigation
             │
             ▼
       Overall Risk View
```

Risk levels include:

```text
LOW
MEDIUM
HIGH
```

The reporting layer aggregates persisted findings to provide the overall operational risk view.

---

# 9. Project Structure

```text
razcontrol-ai/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   ├── detect.py
│   │   │   ├── guard.py
│   │   │   ├── investigate.py
│   │   │   └── report.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── reconciliation.py
│   │   │   ├── control_engine.py
│   │   │   ├── anomaly_detection.py
│   │   │   ├── investigation.py
│   │   │   └── reporting.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   │
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .venv/
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

# 10. Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic

### Database

- PostgreSQL
- pgvector

### Financial Intelligence

- Deterministic reconciliation
- Rule-based financial controls
- Historical IQR anomaly detection
- Evidence-grounded investigation
- Risk aggregation

### Frontend

- HTML
- CSS
- JavaScript

### Infrastructure

- Docker
- Docker Compose
- PostgreSQL
- Redis
- Nginx

### Development

- Git
- GitHub
- Python virtual environment
- REST APIs
- Python `unittest`

---

# 11. API Groups

- `/reconciliation`: run and list reconciliation results.
- `/guard`: scan controls, list findings, summaries, and update finding status.
- `/detect`: run detection, list filtered anomalies, and view summaries.
- `/investigations`: run, list, inspect evidence, and update investigations.
- `/reports`: overall/summary reports, transaction risk, finding lookup, and CSV export.
- `/pipeline/run`: execute Recon, Guard, Detect, optional Investigate, and Report in order.

Pipeline execution:

```text
RazRecon
    ↓
RazGuard
    ↓
RazDetect
    ↓
RazInvestigate (optional)
    ↓
RazReport
```

---

# 12. Local Setup

1. Create a virtual environment in `backend/.venv` and install dependencies:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. Start PostgreSQL. The local database URL is configurable through environment variables. An example development URL is:

```text
postgresql://razcontrol:<password>@localhost:5432/razcontrol
```

3. Start the API from `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

4. Start the dashboard in another terminal:

```powershell
python -m http.server 5173 -d frontend
```

Open:

```text
http://localhost:5173
```

The application reads process environment variables first. For local settings, copy `.env.example` to an ignored `.env` in the directory used to start the API, then replace the placeholder password. Never commit `.env`.

---

# 13. Docker

Copy `.env.example` to `.env`, set `POSTGRES_PASSWORD` to a real secret, and run:

```powershell
docker compose up --build
```

Compose starts PostgreSQL, the FastAPI backend on port 8000, the nginx frontend on port 5173, and Redis for future workers.

The backend waits for PostgreSQL health before starting.

The database schema is currently created through SQLAlchemy startup. The SQL files in `backend/migrations/` document incremental integrity changes and should be applied through an explicit migration process before changing an existing production database.

Useful commands:

```powershell
docker compose ps
docker compose logs
docker compose down
```

---

# 14. Environment Variables

Supported backend variables:

```text
DATABASE_URL
DEBUG
CORS_ORIGINS
ANOMALY_MIN_HISTORY
ANOMALY_IQR_MULTIPLIER
ANOMALY_MIN_RISK_SCORE
ANOMALY_USE_ML
INVESTIGATION_PROVIDER
PIPELINE_MAX_INVESTIGATIONS
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
```

Example development configuration:

```env
DATABASE_URL=postgresql://razcontrol:razcontrol_dev@localhost:5432/razcontrol

DEBUG=true

CORS_ORIGINS=http://localhost:5173

ANOMALY_MIN_HISTORY=30
ANOMALY_IQR_MULTIPLIER=1.5
ANOMALY_MIN_RISK_SCORE=0.0
ANOMALY_USE_ML=false

INVESTIGATION_PROVIDER=evidence_only
PIPELINE_MAX_INVESTIGATIONS=50

POSTGRES_DB=razcontrol
POSTGRES_USER=razcontrol
POSTGRES_PASSWORD=razcontrol_dev
```

Never commit:

```text
.env
```

---

# 15. API Documentation

When the backend is running, interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

The dashboard itself consumes the REST API and provides the primary demonstration interface.

---

# 16. Testing

Run the complete backend suite with the repository virtual environment:

```powershell
$env:PYTHONPATH=(Resolve-Path backend).Path

cd backend

Get-ChildItem tests -Filter 'test_*.py' |
ForEach-Object {
    .\.venv\Scripts\python.exe $_.FullName
}
```

Run compilation checks:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app tests
```

The repository currently has backend `unittest` coverage and no Node package or dedicated frontend test runner.

The current verified backend test result is:

```text
40 tests passed
```

The dashboard has also been smoke-tested through its live API-backed routes.

---

# 17. Idempotency

RazControl is designed to avoid blindly duplicating persisted results when stages are repeated.

### RazRecon

Reconciliation results are associated with bank transactions. Previously persisted confirmed matches are respected, and confirmed GL transaction IDs are reserved to maintain one-to-one matching.

### RazGuard

Control findings use deterministic fingerprints. Repeated scans refresh existing findings rather than blindly creating duplicates.

### RazDetect

Anomaly records use deterministic fingerprints based on detection information and transaction identity.

### RazInvestigate

Investigations use deterministic target fingerprints so repeated execution does not create duplicate investigations for the same target.

### RazReport

RazReport is read-only aggregation and does not create financial findings.

---

# 18. Current Verified Results

The current verified local dataset contains:

### GL Transactions

```text
10,000
```

### Bank Transactions

```text
5,020
```

### Reconciliation

```text
MATCHED       4,764
REVIEW          241
UNMATCHED        15
--------------------
TOTAL         5,020
```

### Control Findings

```text
HIGH_VALUE_TRANSACTION       8,029
WEEKEND_TRANSACTION          2,883
RECONCILIATION_EXCEPTION       256
----------------------------------
TOTAL                       11,168
```

Severity:

```text
HIGH        8,044
MEDIUM      3,124
LOW             0
```

### Anomalies

```text
TOTAL          45
HIGH           41
MEDIUM          4
LOW             0
```

### Investigations

```text
TOTAL                  50
REVIEW_REQUIRED        50
OPEN                    0
INVESTIGATING           0
RESOLVED                0
```

Investigation targets:

```text
Anomaly investigations       41
Control-finding investigations 9
```

### Overall Risk

```text
HIGH
```

---

# 19. Understanding the Results

## Why are there 11,168 control findings for 10,000 GL transactions?

The `11,168` figure represents persisted **control findings**, not unique transactions.

A single transaction can trigger multiple controls.

For example:

```text
Transaction
     │
     ├── HIGH_VALUE_TRANSACTION
     │
     └── WEEKEND_TRANSACTION
```

That transaction produces two findings.

The current dataset contains:

```text
11,168 control findings
8,584 distinct GL transactions with control findings
```

## Why are reconciliation counts based on 5,020?

Reconciliation is performed over the bank transaction population:

```text
5,020 bank transactions
```

The GL population is:

```text
10,000 GL transactions
```

These are different source populations and therefore their totals are not expected to match.

## High-risk report rows

The current report contains:

```text
8,100 high-risk report rows
```

Composition:

```text
8,044 HIGH control findings
   41 HIGH anomalies
   15 UNMATCHED reconciliation report rows
--------------------------------------------
8,100
```

This is a flattened report-row count, not a count of unique underlying business cases.

The 15 unmatched reconciliation cases are represented in both the Guard finding view and the direct reconciliation report view. This is a reporting representation and does not indicate duplicate database persistence.

---

# 20. Safe Numbers for Demonstration

For a live demonstration, the following wording is recommended:

- **10,000 GL transactions monitored**
- **5,020 bank transactions reconciled**
- **4,764 matched**
- **241 requiring review**
- **15 unmatched**
- **11,168 persisted control findings**
- **45 anomalies detected**
- **50 investigation records generated for review**
- **Overall risk: HIGH**

Avoid describing `11,168` as unique transactions.

Avoid describing the 50 investigations as completed or resolved investigations because their current status is `REVIEW_REQUIRED`.

---

# 21. 5-Minute Demo Flow

The recommended demonstration order is:

```text
GitHub README
      ↓
Problem Statement
      ↓
Solution
      ↓
Architecture Diagram
      ↓
VS Code Project Structure
      ↓
RazRecon Implementation
      ↓
RazGuard Implementation
      ↓
RazDetect / RazInvestigate
      ↓
Live Dashboard
      ↓
Overview
      ↓
Reconciliation
      ↓
Controls
      ↓
Anomalies
      ↓
Investigations
      ↓
Reports
```

### Suggested timing

| Time | Section |
|---|---|
| 0:00 – 0:30 | Problem |
| 0:30 – 0:55 | Solution |
| 0:55 – 1:30 | Architecture |
| 1:30 – 2:45 | Implementation |
| 2:45 – 3:25 | Overview |
| 3:25 – 3:45 | Reconciliation |
| 3:45 – 4:05 | Controls |
| 4:05 – 4:20 | Anomalies |
| 4:20 – 4:38 | Investigations |
| 4:38 – 4:52 | Reports |
| 4:52 – 5:00 | Closing |

---

# 22. Demo Architecture Narrative

A concise explanation for a presentation is:

> "Financial data is persisted in PostgreSQL. RazRecon performs bank-to-GL reconciliation using amount, date, and description similarity. RazGuard then applies deterministic financial controls. RazDetect adds historical statistical anomaly detection. High-risk findings can be passed to RazInvestigate, which works from persisted evidence. RazReport aggregates the outputs and FastAPI exposes them to the frontend dashboard."

The complete conceptual flow is:

**Financial Data → PostgreSQL → RazRecon → RazGuard → RazDetect → RazInvestigate → RazReport → FastAPI → Dashboard**

---

# 23. Security

The current project includes:

- Environment-based configuration.
- `.env` exclusion from Git.
- Configurable CORS.
- API input validation.
- Persisted evidence.
- Deterministic financial decisions.
- Separation between financial controls and investigation.
- No requirement to store secrets in source code.

Production deployment should additionally implement:

```text
Authentication
Authorization
TLS
Rate Limiting
Centralized Logging
Audit Logging
Secrets Management
Monitoring
Alerting
Database Backups
Automated Database Migrations
Network Security
```

---

# 24. Performance Considerations

For larger production datasets, recommended optimizations include:

- Database indexing.
- Query optimization.
- Pagination.
- Batch processing.
- Background workers.
- Caching.
- Asynchronous processing.
- Incremental anomaly detection.
- Efficient historical-window queries.

Redis is included in the Docker environment as infrastructure for future worker-based processing.

---

# 25. Limitations

### Authentication

The current local dashboard does not provide a complete production authentication and authorization layer.

### Frontend Testing

There is currently no dedicated Node-based frontend test runner.

### Database Migrations

Migration files document incremental integrity changes, but a complete production migration workflow should use an explicit migration framework.

### Production Infrastructure

The current project is optimized for local demonstration and controlled deployment rather than a fully hardened enterprise production environment.

### Historical Finding Lifecycle

Repeated processing refreshes active findings but does not automatically remove every historical or stale finding when source conditions disappear.

---

# 26. Future Scope

### Advanced AI Investigation

- LLM-based investigation provider.
- Structured LLM outputs.
- Function/tool calling.
- Evidence citation enforcement.
- Confidence estimation.
- Investigation summarization.

### Advanced Anomaly Detection

- Isolation Forest.
- Autoencoders.
- Temporal anomaly detection.
- Vendor-level behavior modeling.
- Account-level risk modeling.
- Ensemble anomaly detection.

### Enterprise Security

- OAuth2 / OpenID Connect.
- Role-based access control.
- JWT authentication.
- Audit trails.
- Enterprise secrets management.

### Scalability

- Redis workers.
- Background processing.
- Kafka-based event ingestion.
- Distributed anomaly detection.
- Large-scale batch processing.

### Database

- Alembic migrations.
- Additional indexes.
- Partitioning for large transaction volumes.
- Read replicas.
- Optimized reporting tables.

### Observability

- Prometheus.
- Grafana.
- Centralized logs.
- Application tracing.
- Alerting.

---

# 27. Docker Deployment Architecture

```mermaid
flowchart LR
    USER[User / Browser] --> FRONT[Nginx Frontend]
    FRONT --> API[FastAPI Backend]

    API --> DB[(PostgreSQL)]
    API --> REDIS[(Redis)]

    API --> RECON[RazRecon]
    API --> GUARD[RazGuard]
    API --> DETECT[RazDetect]
    API --> INVEST[RazInvestigate]
    API --> REPORT[RazReport]

    RECON --> DB
    GUARD --> DB
    DETECT --> DB
    INVEST --> DB
    REPORT --> DB
```

---

# 28. Development Workflow

```text
1. Start PostgreSQL / Redis
          ↓
2. Start FastAPI backend
          ↓
3. Verify API / Swagger
          ↓
4. Start frontend
          ↓
5. Verify dashboard
          ↓
6. Run tests
          ↓
7. Review Git changes
          ↓
8. Commit validated changes
```

---

# 29. Git Safety

Before committing changes:

```powershell
git status
```

Review the diff:

```powershell
git diff
```

Check whitespace:

```powershell
git diff --check
```

Stage intended files:

```powershell
git add .
```

Review staged changes:

```powershell
git diff --cached
```

Commit:

```powershell
git commit -m "Update RazControl AI"
```

Push:

```powershell
git push origin main
```

Never commit:

```text
.env
credentials
API keys
database passwords
virtual environments
generated secrets
```

---

# 30. Project Status

| Component | Status |
|---|---|
| RazRecon | Complete |
| RazGuard | Complete |
| RazDetect | Complete |
| RazInvestigate | Complete |
| RazReport | Complete |
| Backend Integration | Complete |
| Frontend Dashboard | Complete |
| API Integration | Complete |
| Database Persistence | Complete |
| Idempotency | Verified |
| Backend Tests | 40 Passed |
| Frontend Smoke Test | Passed |
| Docker Configuration | Available |
| Production Authentication | Future Work |
| Automated DB Migrations | Future Work |
| Frontend Test Runner | Future Work |

---

# 31. Verification Summary

The current implementation has been verified through:

```text
Backend Tests
      ↓
Python Compilation
      ↓
API Validation
      ↓
Database Verification
      ↓
Frontend Smoke Testing
      ↓
Dashboard Route Verification
```

Latest verified backend result:

```text
40 backend tests passed
```

Latest verified dashboard state:

```text
10,000 GL transactions
5,020 bank transactions
4,764 matched
241 review
15 unmatched
11,168 control findings
45 anomalies
50 investigations
HIGH overall risk
```

---

# 32. Recommended Pitch Closing

> **"RazControl AI brings reconciliation, deterministic financial controls, anomaly detection, evidence-grounded investigation, and risk reporting into one auditable operational platform."**

The core workflow is:

```text
Reconcile
    ↓
Control
    ↓
Detect
    ↓
Investigate
    ↓
Report
    ↓
Act
```

---

# 33. Conclusion

RazControl AI provides an end-to-end financial-control workflow covering:

```text
Bank-to-GL Reconciliation
          ↓
Deterministic Financial Controls
          ↓
Statistical Anomaly Detection
          ↓
Evidence-Grounded Investigation
          ↓
Risk Aggregation
          ↓
Operational Dashboard
```

The system combines deterministic financial logic with evidence-grounded investigation to provide a transparent, explainable, and auditable approach to financial risk management.

The current implementation is integrated across the backend, database, pipeline services, APIs, and frontend dashboard.

---

## Project Status

**RazControl AI is fully implemented and locally verified for the current application and dashboard scope.**

Production enterprise capabilities such as authentication, authorization, TLS, centralized monitoring, automated migrations, and large-scale distributed processing remain future deployment enhancements rather than blockers for the current demonstration scope.
