# RazControl AI

> **AI-assisted financial control, reconciliation, anomaly detection, investigation, and risk reporting platform.**

RazControl AI is a deterministic financial-control pipeline with an evidence-grounded investigation stage and a web-based operations dashboard.

It processes persisted General Ledger (GL) and bank transaction data through a sequence of financial-control stages:

- **RazRecon** — one-to-one bank-to-GL reconciliation with `MATCHED`, `REVIEW`, and `UNMATCHED` outcomes.
- **RazGuard** — deterministic financial control rules covering materiality, duplicates, dates, data quality, and reconciliation exceptions.
- **RazDetect** — explainable historical IQR-based anomaly detection with explicit control and reconciliation risk modifiers.
- **RazInvestigate** — evidence-only investigation workflow that uses persisted source records and avoids asserting unsupported causes.
- **RazReport** — read-only risk summaries, finding details, transaction risk views, and CSV export.
- **Frontend Dashboard** — a static operations dashboard connected to the FastAPI backend for live metrics, findings, filters, actions, and reports.

---

# 1. Problem Statement

Financial control teams often need to analyze large volumes of transactions across multiple sources while identifying:

- Bank-to-GL reconciliation exceptions
- High-value transactions
- Duplicate or suspicious transactions
- Weekend or unusual-date transactions
- Data-quality issues
- Statistical anomalies
- High-risk findings requiring investigation

Traditional workflows can require significant manual effort to reconcile transactions, identify exceptions, investigate findings, and prepare reports.

The challenge is to build a system that can process financial data systematically while keeping financial-control decisions explainable and auditable.

---

# 2. Solution

RazControl AI addresses this problem through a layered financial-control pipeline.

The system separates deterministic financial controls from anomaly detection and evidence-based investigation.

```mermaid
flowchart TD
    A[GL Transactions] --> B[(PostgreSQL)]
    C[Bank Transactions] --> B

    B --> D[RazRecon]
    D --> E[RazGuard]
    D --> F[RazDetect]

    E --> G[RazInvestigate]
    F --> G

    D --> H[RazReport]
    E --> H
    F --> H
    G --> H

    H --> I[RazControl Dashboard]

    J[Redis] -. Runtime / Cache Support .-> D
    J -. Runtime / Cache Support .-> E
    J -. Runtime / Cache Support .-> F
    J -. Runtime / Cache Support .-> G