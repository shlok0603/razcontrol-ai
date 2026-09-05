# RazControl AI

> **AI-powered financial control, reconciliation, anomaly detection, investigation, and risk reporting platform.**

RazControl AI is a deterministic financial-control pipeline with an evidence-grounded investigation stage and a static operations dashboard.

It processes persisted transaction and bank data through a sequence of specialized modules:

- **RazRecon** — one-to-one bank-to-GL reconciliation with MATCHED, REVIEW, and UNMATCHED outcomes.
- **RazGuard** — deterministic financial control rules for materiality, duplicates, dates, data quality, and reconciliation exceptions.
- **RazDetect** — explainable historical IQR-based anomaly detection with explicit control and reconciliation risk-score modifiers.
- **RazInvestigate** — evidence-only investigations that cite persisted source records and do not assert unsourced causes.
- **RazReport** — read-only risk summaries, finding details, transaction risk views, and CSV export.
- **Frontend Dashboard** — static operations dashboard for live metrics, findings, actions, filters, investigations, and reports.

---

# Table of Contents

- [Problem](#problem)
- [Solution](#solution)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [End-to-End Data Flow](#end-to-end-data-flow)
- [Module Flow](#module-flow)
- [Risk Detection Flow](#risk-detection-flow)
- [Investigation Flow](#investigation-flow)
- [Reporting Flow](#reporting-flow)
- [Database Architecture](#database-architecture)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Local Setup](#local-setup)
- [Docker](#docker)
- [Running the Dashboard](#running-the-dashboard)
- [API Groups](#api-groups)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Demo Flow](#demo-flow)
- [Current Verified Results](#current-verified-results)
- [Data Interpretation](#data-interpretation)
- [Security and Production Considerations](#security-and-production-considerations)
- [Limitations and Future Improvements](#limitations-and-future-improvements)

---

# Problem

Financial operations teams often need to process large amounts of transaction data across multiple systems.

Typical challenges include:

- Bank transactions not matching ledger transactions.
- Duplicate or suspicious transactions.
- High-value transactions requiring additional review.
- Weekend or unusual-date transactions.
- Data-quality issues.
- Transaction anomalies that are difficult to identify manually.
- Risk findings spread across multiple systems.
- Investigations requiring manual evidence gathering.
- Lack of a unified operational dashboard.
- Difficulty producing consistent audit-ready reports.

Traditional workflows can require analysts to manually reconcile transactions, inspect exceptions, investigate suspicious activity, and prepare reports.

RazControl AI addresses this by combining deterministic financial controls with explainable anomaly detection and evidence-grounded investigation.

---

# Solution

RazControl AI creates a complete financial-risk processing pipeline:

```mermaid
flowchart TD

    A[Financial Data] --> B[RazRecon]

    B --> C[MATCHED]
    B --> D[REVIEW]
    B --> E[UNMATCHED]

    C --> F[RazGuard]
    D --> F
    E --> F

    F --> G[Control Findings]

    G --> H[RazDetect]
    H --> I[Anomaly Findings]

    G --> J[RazInvestigate]
    I --> J

    J --> K[Evidence-Grounded Investigation]

    G --> L[RazReport]
    I --> L
    J --> L
    B --> L

    L --> M[Risk Summary]
    L --> N[CSV Export]

    M --> O[Operations Dashboard]
    N --> O