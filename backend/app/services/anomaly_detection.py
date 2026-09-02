"""Explainable historical anomaly detection for RazDetect."""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
import logging
from statistics import median
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Anomaly, ControlFinding, ReconciliationMatch, Transaction

logger = logging.getLogger(__name__)
METHOD = "HISTORICAL_IQR_V1"


def _quantile(values: list[Decimal], fraction: float) -> Decimal:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower, upper = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * Decimal(str(position - lower))


def prepare_transactions(db: Session) -> list[Transaction]:
    """Load only columns-backed transaction records once, ordered for history-safe scoring."""
    return db.query(Transaction).order_by(Transaction.transaction_date, Transaction.id).all()


def prepare_context(db: Session) -> tuple[dict[str, list[ControlFinding]], dict[str, ReconciliationMatch]]:
    controls: dict[str, list[ControlFinding]] = defaultdict(list)
    for finding in db.query(ControlFinding).filter(ControlFinding.record_type == "Transaction", ControlFinding.status.in_(("OPEN", "IN_REVIEW"))).all():
        if finding.record_id:
            controls[finding.record_id].append(finding)
    recon = {item.transaction_id: item for item in db.query(ReconciliationMatch).filter(ReconciliationMatch.transaction_id.isnot(None), ReconciliationMatch.status != "MATCHED").all()}
    return controls, recon


def engineer_features(transactions: list[Transaction]) -> list[tuple[Transaction, dict[str, Any]]]:
    """Use prior dates only, preventing a transaction from influencing its own baseline."""
    history: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    result = []
    index = 0
    while index < len(transactions):
        current_date = transactions[index].transaction_date
        same_day = []
        while index < len(transactions) and transactions[index].transaction_date == current_date:
            same_day.append(transactions[index]); index += 1
        baselines: dict[tuple[str, str], dict[str, Any]] = {}
        for transaction in same_day:
            key = (transaction.account or "__UNASSIGNED__", transaction.currency)
            amounts = history[key]
            if key not in baselines:
                baselines[key] = {"history_count": len(amounts)}
                if amounts:
                    baselines[key].update({"historical_median": float(median(amounts)), "q1": float(_quantile(amounts, .25)), "q3": float(_quantile(amounts, .75))})
            features: dict[str, Any] = {"baseline_group": {"account": transaction.account, "currency": transaction.currency}, **baselines[key], "amount": float(abs(transaction.amount))}
            result.append((transaction, features))
        for transaction in same_day:
            history[(transaction.account or "__UNASSIGNED__", transaction.currency)].append(abs(transaction.amount))
    return result


def score_features(features: dict[str, Any]) -> tuple[float, str | None, dict[str, Any]]:
    if features["history_count"] < settings.ANOMALY_MIN_HISTORY:
        return 0.0, None, features
    q1, q3 = Decimal(str(features["q1"])), Decimal(str(features["q3"]))
    amount = Decimal(str(features["amount"]))
    iqr = q3 - q1
    lower, upper = q1 - Decimal(str(settings.ANOMALY_IQR_MULTIPLIER)) * iqr, q3 + Decimal(str(settings.ANOMALY_IQR_MULTIPLIER)) * iqr
    features.update({"iqr": float(iqr), "lower_bound": float(lower), "upper_bound": float(upper)})
    if lower <= amount <= upper:
        return 0.0, None, features
    if iqr == 0:
        score = 90.0
    else:
        distance = (amount - upper) / iqr if amount > upper else (lower - amount) / iqr
        score = min(95.0, 60.0 + float(distance) * 10.0)
    direction = "above" if amount > upper else "below"
    reason = f"Transaction amount {amount:.2f} is {direction} the historical IQR range {lower:.2f} to {upper:.2f} for its account and currency baseline."
    return score, reason, features


def _severity(score: float) -> str:
    return "HIGH" if score >= 80 else "MEDIUM" if score >= 60 else "LOW"


def detect_anomalies(db: Session) -> list[dict[str, Any]]:
    """Run the configurable deterministic baseline and persist idempotent results."""
    try:
        transactions = prepare_transactions(db)
        control_context, recon_context = prepare_context(db)
        candidates = []
        for transaction, features in engineer_features(transactions):
            score, reason, evidence = score_features(features)
            if reason is None:
                continue
            controls = control_context.get(transaction.transaction_id, [])
            reconciliation = recon_context.get(transaction.transaction_id)
            modifiers = []
            if controls:
                highest = "HIGH" if any(item.severity == "HIGH" for item in controls) else "MEDIUM"
                increment = 10.0 if highest == "HIGH" else 5.0
                score = min(100.0, score + increment)
                modifiers.append({"source": "RazGuard", "severity": highest, "control_ids": [item.control_id for item in controls], "score_adjustment": increment})
            if reconciliation:
                increment = 10.0 if reconciliation.status == "UNMATCHED" else 5.0
                score = min(100.0, score + increment)
                modifiers.append({"source": "RazRecon", "status": reconciliation.status, "confidence": float(reconciliation.confidence), "score_adjustment": increment})
            if score >= settings.ANOMALY_MIN_RISK_SCORE:
                evidence["modifiers"] = modifiers
                candidates.append({"transaction": transaction, "score": round(score, 2), "reason": reason, "evidence": evidence})
        persisted = [_persist_anomaly(db, candidate) for candidate in candidates]
        db.commit()
        return [serialize_anomaly(item) for item in persisted]
    except Exception:
        db.rollback()
        logger.exception("RazDetect run failed")
        raise


def _persist_anomaly(db: Session, candidate: dict[str, Any]) -> Anomaly:
    transaction = candidate["transaction"]
    fingerprint = sha256(f"{METHOD}|AMOUNT_IQR_DEVIATION|{transaction.transaction_id}".encode()).hexdigest()
    anomaly = db.query(Anomaly).filter_by(fingerprint=fingerprint).one_or_none()
    now = datetime.now(UTC).replace(tzinfo=None)
    values = {"risk_score": Decimal(str(candidate["score"])), "severity": _severity(candidate["score"]), "explanation": candidate["reason"], "evidence": candidate["evidence"], "last_seen_at": now}
    if anomaly is None:
        anomaly = Anomaly(anomaly_id=f"ANOM-{uuid4().hex[:16].upper()}", fingerprint=fingerprint, transaction_id=transaction.transaction_id, anomaly_type="AMOUNT_IQR_DEVIATION", detected_by="RazDetect", detection_method=METHOD, status="OPEN", created_at=now, **values)
        db.add(anomaly)
    else:
        anomaly.risk_score, anomaly.severity, anomaly.explanation, anomaly.evidence, anomaly.last_seen_at = values["risk_score"], values["severity"], values["explanation"], values["evidence"], now
    return anomaly


def serialize_anomaly(item: Anomaly) -> dict[str, Any]:
    return {"anomaly_id": item.anomaly_id, "transaction_id": item.transaction_id, "anomaly_type": item.anomaly_type, "risk_score": float(item.risk_score), "severity": item.severity, "detection_method": item.detection_method, "explanation": item.explanation, "evidence": item.evidence, "status": item.status, "detected_at": item.created_at.isoformat(), "last_seen_at": item.last_seen_at.isoformat()}


def get_anomalies(db: Session, severity: str | None = None, status: str | None = None, transaction_id: str | None = None) -> list[dict[str, Any]]:
    query = db.query(Anomaly)
    if severity: query = query.filter(Anomaly.severity == severity)
    if status: query = query.filter(Anomaly.status == status)
    if transaction_id: query = query.filter(Anomaly.transaction_id == transaction_id)
    return [serialize_anomaly(item) for item in query.order_by(Anomaly.risk_score.desc(), Anomaly.created_at.desc()).all()]


def anomaly_summary(db: Session) -> dict[str, Any]:
    records = db.query(Anomaly).all()
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for item in records: counts[item.severity] = counts.get(item.severity, 0) + 1
    return {"total_anomalies": len(records), "open_anomalies": sum(item.status == "OPEN" for item in records), "by_severity": counts, "method": METHOD, "ml_enabled": settings.ANOMALY_USE_ML}
