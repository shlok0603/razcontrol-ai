# RazControl AI

> **AI-powered financial control, reconciliation, anomaly detection, investigation, and risk reporting platform.**

RazControl AI is a deterministic financial-control platform designed to help financial operations teams identify reconciliation exceptions, control violations, anomalous transactions, and high-risk financial activity through a unified processing and investigation pipeline.

The system combines **deterministic financial rules**, **explainable anomaly detection**, **evidence-grounded investigation**, and **risk reporting** into a single workflow.

---

# Overview

RazControl AI processes financial transaction data through a structured control pipeline:

```text
Financial Data
      │
      ▼
┌─────────────────────┐
│      RazRecon       │
│ Reconciliation      │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│      RazGuard       │
│ Financial Controls  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│      RazDetect      │
│ Anomaly Detection   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   RazInvestigate    │
│ Evidence Analysis   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│      RazReport      │
│ Risk & Reporting    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   RazControl UI     │
│ Operations Dashboard│
└─────────────────────┘