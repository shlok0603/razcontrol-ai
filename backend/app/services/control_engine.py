"""Deterministic persisted financial controls for RazGuard."""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
import logging
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import ControlFinding, FinancialControl, ReconciliationMatch, Transaction

logger = logging.getLogger(__name__)

CONTROL_CATALOG: tuple[dict[str, Any], ...] = (
    {"control_id": "HIGH_VALUE_TRANSACTION", "name": "High-value transaction", "description": "Flags transactions above the configured materiality threshold.", "category": "Transaction monitoring", "default_severity": "HIGH", "rule_definition": {"threshold": 100000}, "detection_logic": "high_value_transaction"},
    {"control_id": "ROUND_AMOUNT", "name": "Large round-value transaction", "description": "Flags material transactions recorded as large round amounts.", "category": "Transaction monitoring", "default_severity": "MEDIUM", "rule_definition": {"minimum_amount": 10000, "increment": 10000}, "detection_logic": "round_amount"},
    {"control_id": "WEEKEND_TRANSACTION", "name": "Weekend transaction", "description": "Flags transactions dated on Saturday or Sunday.", "category": "Date controls", "default_severity": "MEDIUM", "rule_definition": {}, "detection_logic": "weekend_transaction"},
    {"control_id": "DUPLICATE_TRANSACTION", "name": "Potential duplicate transaction", "description": "Flags GL transactions with the same amount, date, description, vendor, currency, and type.", "category": "Duplicate detection", "default_severity": "HIGH", "rule_definition": {}, "detection_logic": "duplicate_transaction"},
    {"control_id": "MISSING_TRANSACTION_INFORMATION", "name": "Missing transaction information", "description": "Flags transactions missing optional operational fields required by this control policy.", "category": "Data quality", "default_severity": "MEDIUM", "rule_definition": {"required_fields": ["vendor", "account", "transaction_type", "source"]}, "detection_logic": "missing_transaction_information"},
    {"control_id": "INVALID_TRANSACTION_FIELDS", "name": "Inconsistent transaction fields", "description": "Flags invalid currency codes or unrecognised transaction types.", "category": "Data quality", "default_severity": "MEDIUM", "rule_definition": {"transaction_types": ["DEBIT", "CREDIT"]}, "detection_logic": "invalid_transaction_fields"},
    {"control_id": "RECONCILIATION_EXCEPTION", "name": "Reconciliation exception", "description": "Flags RazRecon results that require review or remain unmatched.", "category": "Reconciliation", "default_severity": "MEDIUM", "rule_definition": {"REVIEW": "MEDIUM", "UNMATCHED": "HIGH"}, "detection_logic": "reconciliation_exception"},
)


def ensure_control_catalog(db: Session) -> list[FinancialControl]:
    existing = {item.control_id: item for item in db.query(FinancialControl).all()}
    for definition in CONTROL_CATALOG:
        if definition["control_id"] not in existing:
            item = FinancialControl(enabled=True, **definition)
            db.add(item)
            existing[item.control_id] = item
    db.flush()
    return list(existing.values())


def _evidence(t: Transaction) -> dict[str, Any]:
    return {"transaction_id": t.transaction_id, "amount": float(t.amount), "transaction_date": t.transaction_date.isoformat(), "description": t.description, "vendor": t.vendor, "account": t.account, "currency": t.currency, "transaction_type": t.transaction_type, "source": t.source}


def _finding(c: FinancialControl, record_id: str, evidence: dict[str, Any], explanation: str, severity: str | None = None, record_type: str = "Transaction") -> dict[str, Any]:
    return {"control_id": c.control_id, "title": c.name, "record_type": record_type, "record_id": record_id, "severity": severity or c.default_severity, "evidence": evidence, "explanation": explanation}


def high_value(c: FinancialControl, rows: list[Transaction]) -> list[dict[str, Any]]:
    threshold = Decimal(str(c.rule_definition["threshold"]))
    return [_finding(c, t.transaction_id, {**_evidence(t), "threshold": float(threshold)}, f"Transaction {t.transaction_id} is {abs(t.amount):.2f}, above the configured threshold of {threshold:.2f}.") for t in rows if abs(t.amount) > threshold]


def round_amount(c: FinancialControl, rows: list[Transaction]) -> list[dict[str, Any]]:
    minimum, increment = Decimal(str(c.rule_definition["minimum_amount"])), Decimal(str(c.rule_definition["increment"]))
    return [_finding(c, t.transaction_id, {**_evidence(t), "minimum_amount": float(minimum), "increment": float(increment)}, f"Transaction {t.transaction_id} has a material round amount of {abs(t.amount):.2f}.") for t in rows if abs(t.amount) >= minimum and abs(t.amount) % increment == 0]


def weekend(c: FinancialControl, rows: list[Transaction]) -> list[dict[str, Any]]:
    return [_finding(c, t.transaction_id, _evidence(t), f"Transaction {t.transaction_id} is dated {t.transaction_date.isoformat()}, a {t.transaction_date.strftime('%A')}.") for t in rows if t.transaction_date.weekday() >= 5]


def duplicates(c: FinancialControl, rows: list[Transaction]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[Transaction]] = defaultdict(list)
    for t in rows:
        groups[(t.amount, t.transaction_date, t.description, t.vendor, t.currency, t.transaction_type)].append(t)
    result = []
    for group in groups.values():
        if len(group) > 1:
            ids = sorted(t.transaction_id for t in group)
            for t in group:
                peers = [item for item in ids if item != t.transaction_id]
                result.append(_finding(c, t.transaction_id, {**_evidence(t), "duplicate_transaction_ids": peers, "duplicate_count": len(group)}, f"Transaction {t.transaction_id} shares amount, date, description, vendor, currency, and type with {', '.join(peers)}."))
    return result


def missing_information(c: FinancialControl, rows: list[Transaction]) -> list[dict[str, Any]]:
    required = c.rule_definition["required_fields"]
    result = []
    for t in rows:
        missing = [field for field in required if not getattr(t, field)]
        if missing:
            result.append(_finding(c, t.transaction_id, {**_evidence(t), "missing_fields": missing}, f"Transaction {t.transaction_id} is missing required control fields: {', '.join(missing)}."))
    return result


def invalid_fields(c: FinancialControl, rows: list[Transaction]) -> list[dict[str, Any]]:
    allowed = set(c.rule_definition["transaction_types"])
    result = []
    for t in rows:
        invalid = []
        if len(t.currency or "") != 3 or t.currency != t.currency.upper(): invalid.append("currency")
        if t.transaction_type not in allowed: invalid.append("transaction_type")
        if invalid:
            result.append(_finding(c, t.transaction_id, {**_evidence(t), "invalid_fields": invalid, "allowed_transaction_types": sorted(allowed)}, f"Transaction {t.transaction_id} contains invalid fields: {', '.join(invalid)}."))
    return result


def reconciliation_exception(c: FinancialControl, rows: list[ReconciliationMatch]) -> list[dict[str, Any]]:
    result = []
    for r in rows:
        if r.status != "MATCHED":
            evidence = {"bank_transaction_id": r.bank_transaction_id, "candidate_transaction_id": r.transaction_id, "reconciliation_status": r.status, "confidence": float(r.confidence), "amount_score": float(r.amount_score), "date_score": float(r.date_score), "description_score": float(r.description_score), "reason": r.reason}
            result.append(_finding(c, r.bank_transaction_id, evidence, f"Bank transaction {r.bank_transaction_id} has RazRecon status {r.status}: {r.reason}", c.rule_definition.get(r.status, c.default_severity), "BankTransaction"))
    return result


Evaluator = Callable[[FinancialControl, list[Any]], list[dict[str, Any]]]
EVALUATORS: dict[str, Evaluator] = {"high_value_transaction": high_value, "round_amount": round_amount, "weekend_transaction": weekend, "duplicate_transaction": duplicates, "missing_transaction_information": missing_information, "invalid_transaction_fields": invalid_fields, "reconciliation_exception": reconciliation_exception}


def _persist(db: Session, finding: dict[str, Any]) -> ControlFinding:
    fingerprint = sha256(f"{finding['control_id']}|{finding['record_type']}|{finding['record_id']}".encode()).hexdigest()
    item = db.query(ControlFinding).filter_by(fingerprint=fingerprint).one_or_none()
    now = datetime.now(UTC).replace(tzinfo=None)
    persisted_values = {key: value for key, value in finding.items() if key != "title"}
    if item is None:
        item = ControlFinding(finding_id=f"CF-{uuid4().hex[:16].upper()}", fingerprint=fingerprint, status="OPEN", detected_at=now, **persisted_values)
        db.add(item)
    else:
        item.severity, item.evidence, item.explanation, item.last_seen_at = finding["severity"], finding["evidence"], finding["explanation"], now
    return item


def serialize_finding(item: ControlFinding) -> dict[str, Any]:
    return {"finding_id": item.finding_id, "control_id": item.control_id, "rule_id": item.control_id, "title": item.control_id.replace("_", " ").title(), "record_type": item.record_type, "record_id": item.record_id, "transaction_id": item.record_id if item.record_type == "Transaction" else None, "status": item.status, "severity": item.severity, "evidence": item.evidence, "explanation": item.explanation, "description": item.explanation, "detected_at": item.detected_at.isoformat(), "last_seen_at": item.last_seen_at.isoformat()}


def run_control_engine(db: Session) -> list[dict[str, Any]]:
    try:
        controls = [item for item in ensure_control_catalog(db) if item.enabled]
        transactions = db.query(Transaction).all()
        recon = db.query(ReconciliationMatch).filter(ReconciliationMatch.status != "MATCHED").all()
        persisted = []
        for control in controls:
            evaluator = EVALUATORS.get(control.detection_logic)
            if evaluator is None:
                logger.warning("Skipping unknown control logic: %s", control.detection_logic)
                continue
            source = recon if control.detection_logic == "reconciliation_exception" else transactions
            persisted.extend(_persist(db, finding) for finding in evaluator(control, source))
        db.commit()
        return [serialize_finding(item) for item in persisted]
    except Exception:
        db.rollback()
        logger.exception("RazGuard control run failed")
        raise


def get_findings(db: Session, control_id: str | None = None, transaction_id: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    query = db.query(ControlFinding)
    if control_id is not None: query = query.filter(ControlFinding.control_id == control_id)
    if transaction_id is not None: query = query.filter(ControlFinding.record_id == transaction_id)
    if limit is not None: query = query.limit(limit)
    return [serialize_finding(item) for item in query.order_by(ControlFinding.detected_at.desc()).all()]


def findings_summary(db: Session) -> dict[str, Any]:
    findings = db.query(ControlFinding).all()
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for item in findings: counts[item.severity] = counts.get(item.severity, 0) + 1
    return {"total_findings": len(findings), "open_findings": sum(item.status == "OPEN" for item in findings), "by_severity": counts}


def update_finding_status(db: Session, finding_id: str, status: str) -> dict[str, Any] | None:
    if status not in {"OPEN", "IN_REVIEW", "RESOLVED", "DISMISSED"}:
        raise ValueError("status must be OPEN, IN_REVIEW, RESOLVED, or DISMISSED")
    finding = db.query(ControlFinding).filter_by(finding_id=finding_id).one_or_none()
    if finding is None:
        return None
    try:
        finding.status = status
        db.commit()
    except Exception:
        db.rollback()
        raise
    return serialize_finding(finding)
