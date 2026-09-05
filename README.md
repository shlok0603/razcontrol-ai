# RazControl AI

> **AI-powered financial control, reconciliation, anomaly detection, investigation, and risk reporting platform.**

RazControl AI is a deterministic financial-control pipeline with an evidence-grounded investigation stage and a static operations dashboard. It processes persisted transaction and bank data through:

- **RazRecon**: one-to-one bank-to-GL reconciliation with matched, review, and unmatched outcomes.
- **RazGuard**: deterministic control rules for materiality, duplicates, dates, data quality, and reconciliation exceptions.
- **RazDetect**: explainable historical IQR anomaly detection with explicit control and reconciliation score modifiers.
- **RazInvestigate**: evidence-only investigations that cite persisted source records and do not assert unsourced causes.
- **RazReport**: read-only risk summaries, finding details, transaction risk views, and CSV export.
- **Frontend**: the `frontend/` static dashboard for live metrics, findings, actions, filters, and reports.

---

# 1. Problem Statement

Financial operations teams process large volumes of transactions across bank systems, general ledgers, control systems, and reporting workflows.

This creates several challenges:

- Bank transactions may not match GL transactions.
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