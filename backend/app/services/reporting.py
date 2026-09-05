"""Read-only financial risk reporting from persisted RazControl results."""
from __future__ import annotations

import csv
import io
import json
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models import Anomaly, BankTransaction, ControlFinding, Investigation, ReconciliationMatch, Transaction


def _csv_safe(value: Any) -> Any:
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return "'" + value
    return value


def _severity_counts(records: list[Any]) -> dict[str, int]:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for record in records: counts[record.severity] = counts.get(record.severity, 0) + 1
    return counts


def _investigations(db: Session) -> dict[tuple[str, str], Investigation]:
    return {(item.target_type, item.target_id): item for item in db.query(Investigation).all()}


def _recommended(investigation: Investigation | None) -> tuple[str | None, str | None]:
    if investigation is None: return None, "Assign a reviewer and investigate the persisted evidence."
    return investigation.status, investigation.recommended_next_action


def finding_details(db: Session) -> list[dict[str, Any]]:
    investigations = _investigations(db)
    results = []
    for item in db.query(ControlFinding).all():
        status, action = _recommended(investigations.get(("CONTROL_FINDING", item.finding_id)))
        results.append({"finding_id": item.finding_id, "source": "RazGuard", "transaction_id": item.record_id if item.record_type == "Transaction" else None, "record_id": item.record_id, "type": item.control_id, "severity": item.severity, "status": item.status, "evidence": item.evidence, "explanation": item.explanation, "investigation_status": status, "recommended_action": action})
    for item in db.query(Anomaly).all():
        status, action = _recommended(investigations.get(("ANOMALY", item.anomaly_id)))
        results.append({"finding_id": item.anomaly_id, "source": "RazDetect", "transaction_id": item.transaction_id, "record_id": item.transaction_id, "type": item.anomaly_type, "severity": item.severity, "status": item.status, "evidence": item.evidence, "explanation": item.explanation, "investigation_status": status, "recommended_action": action})
    for item in db.query(ReconciliationMatch).filter(ReconciliationMatch.status != "MATCHED").all():
        status, action = _recommended(investigations.get(("RECONCILIATION", item.bank_transaction_id)))
        severity = "HIGH" if item.status == "UNMATCHED" else "MEDIUM"
        results.append({"finding_id": item.bank_transaction_id, "source": "RazRecon", "transaction_id": item.transaction_id, "record_id": item.bank_transaction_id, "type": "RECONCILIATION_EXCEPTION", "severity": severity, "status": item.status, "evidence": {"confidence": float(item.confidence), "amount_score": float(item.amount_score), "date_score": float(item.date_score), "description_score": float(item.description_score)}, "explanation": item.reason, "investigation_status": status, "recommended_action": action})
    return sorted(results, key=lambda item: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(item["severity"], 3), item["finding_id"]))


def report_summary(db: Session) -> dict[str, Any]:
    transactions = db.query(Transaction).count()
    bank = db.query(BankTransaction).all()
    controls = db.query(ControlFinding).all()
    anomalies = db.query(Anomaly).all()
    investigations = db.query(Investigation).all()
    details = finding_details(db)
    high_risk = sum(item["severity"] == "HIGH" for item in details)
    medium_risk = sum(item["severity"] == "MEDIUM" for item in details)
    overall = "HIGH" if high_risk else "MEDIUM" if medium_risk else "LOW"
    return {"total_transactions": transactions, "reconciliation": {"total_bank_transactions": len(bank), "by_status": dict(Counter(item.reconciliation_status for item in bank))}, "control_violations": {"total": len(controls), "by_severity": _severity_counts(controls)}, "anomalies": {"total": len(anomalies), "by_severity": _severity_counts(anomalies)}, "investigations": {"total": len(investigations), "open": sum(item.status in {"OPEN", "INVESTIGATING", "REVIEW_REQUIRED"} for item in investigations), "resolved": sum(item.status == "RESOLVED" for item in investigations)}, "resolved_findings": sum(item.status in {"RESOLVED", "DISMISSED"} for item in controls) + sum(item.status in {"RESOLVED", "DISMISSED"} for item in anomalies), "high_risk_findings": high_risk, "overall_risk": overall}


def overall_report(db: Session, findings_limit: int | None = None) -> dict[str, Any]:
    findings = finding_details(db)
    return {"summary": report_summary(db), "total_findings": len(findings), "findings": findings[:findings_limit] if findings_limit is not None else findings}


def get_finding_report(db: Session, finding_id: str) -> dict[str, Any] | None:
    return next((item for item in finding_details(db) if item["finding_id"] == finding_id), None)


def transaction_risk_report(db: Session, transaction_id: str) -> dict[str, Any]:
    transaction = db.query(Transaction).filter_by(transaction_id=transaction_id).one_or_none()
    findings = [item for item in finding_details(db) if item["transaction_id"] == transaction_id]
    risk = "HIGH" if any(item["severity"] == "HIGH" for item in findings) else "MEDIUM" if findings else "LOW"
    return {"transaction_id": transaction_id, "transaction_exists": transaction is not None, "risk": risk, "findings": findings}


def report_csv(db: Session) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["finding_id", "source", "transaction_id", "record_id", "type", "severity", "status", "investigation_status", "recommended_action", "explanation", "evidence"])
    writer.writeheader()
    for item in finding_details(db):
        writer.writerow({key: _csv_safe(value) for key, value in {**item, "evidence": json.dumps(item["evidence"], sort_keys=True)}.items()})
    return output.getvalue()
