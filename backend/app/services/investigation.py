"""Evidence-grounded RazInvestigate workflow; providers never receive unsourced context."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import logging
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Anomaly, ControlFinding, Investigation, InvestigationEvidence, ReconciliationMatch, Transaction

logger = logging.getLogger(__name__)
ANTI_HALLUCINATION_INSTRUCTIONS = "Use only supplied evidence. Do not invent transactions, amounts, dates, policies, or controls. Mark hypotheses as hypotheses and state when evidence is insufficient. Cite source_type/source_id for every factual conclusion."


@dataclass(frozen=True)
class EvidenceItem:
    source_type: str
    source_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class InvestigationResult:
    summary: str
    risk_assessment: str
    likely_cause: str
    supporting_evidence: list[str]
    conflicting_evidence: list[dict[str, Any]]
    confidence: float
    recommended_next_action: str


class InvestigationProvider(Protocol):
    name: str
    def investigate(self, target_type: str, target_id: str, evidence: list[EvidenceItem], instructions: str) -> InvestigationResult: ...


class EvidenceOnlyProvider:
    """Safe default when no configured external LLM provider exists."""
    name = "evidence_only"

    def investigate(self, target_type: str, target_id: str, evidence: list[EvidenceItem], instructions: str) -> InvestigationResult:
        citations = [f"{item.source_type}:{item.source_id}" for item in evidence]
        if not evidence:
            return InvestigationResult("Evidence is insufficient to investigate this target.", "Unable to assess risk from available records.", "No conclusion can be drawn.", [], [], 0.0, "Collect or link source records, then request human review.")
        primary = evidence[0]
        risk = str(primary.payload.get("severity") or primary.payload.get("risk_score") or primary.payload.get("status") or "requires review")
        return InvestigationResult(f"Evidence-only investigation of {target_type}:{target_id}; {len(evidence)} sourced records were collected.", f"Risk indicator from {primary.source_type}:{primary.source_id} is {risk}.", "A deterministic evidence-only provider is active; no causal conclusion is asserted without an approved LLM provider.", citations, [], 0.4, "Assign a human reviewer and validate the cited records before taking action.")


def get_provider() -> InvestigationProvider:
    # A vendor provider can be registered here after its SDK and credentials are
    # deliberately configured. No API keys are read or logged by this layer.
    return EvidenceOnlyProvider()


def _transaction_payload(item: Transaction) -> dict[str, Any]:
    return {"transaction_id": item.transaction_id, "amount": float(item.amount), "transaction_date": item.transaction_date.isoformat(), "description": item.description, "vendor": item.vendor, "account": item.account, "currency": item.currency, "transaction_type": item.transaction_type, "source": item.source}


def collect_evidence(db: Session, target_type: str, target_id: str) -> list[EvidenceItem]:
    """Retrieve only records linked by the existing schema; no inferred records."""
    evidence: list[EvidenceItem] = []
    transaction_id: str | None = None
    if target_type == "ANOMALY":
        anomaly = db.query(Anomaly).filter_by(anomaly_id=target_id).one_or_none()
        if anomaly is None: return []
        transaction_id = anomaly.transaction_id
        evidence.append(EvidenceItem("Anomaly", anomaly.anomaly_id, {"transaction_id": anomaly.transaction_id, "risk_score": float(anomaly.risk_score), "severity": anomaly.severity, "anomaly_type": anomaly.anomaly_type, "detection_method": anomaly.detection_method, "explanation": anomaly.explanation, "evidence": anomaly.evidence}))
    elif target_type == "CONTROL_FINDING":
        finding = db.query(ControlFinding).filter_by(finding_id=target_id).one_or_none()
        if finding is None: return []
        transaction_id = finding.record_id if finding.record_type == "Transaction" else None
        evidence.append(EvidenceItem("ControlFinding", finding.finding_id, {"control_id": finding.control_id, "record_type": finding.record_type, "record_id": finding.record_id, "severity": finding.severity, "status": finding.status, "explanation": finding.explanation, "evidence": finding.evidence}))
    elif target_type == "RECONCILIATION":
        reconciliation = db.query(ReconciliationMatch).filter_by(bank_transaction_id=target_id).one_or_none()
        if reconciliation is None: return []
        transaction_id = reconciliation.transaction_id
        evidence.append(EvidenceItem("ReconciliationMatch", reconciliation.bank_transaction_id, {"bank_transaction_id": reconciliation.bank_transaction_id, "transaction_id": reconciliation.transaction_id, "status": reconciliation.status, "confidence": float(reconciliation.confidence), "reason": reconciliation.reason}))
    else:
        raise ValueError("target_type must be ANOMALY, CONTROL_FINDING, or RECONCILIATION")

    if transaction_id:
        transaction = db.query(Transaction).filter_by(transaction_id=transaction_id).one_or_none()
        if transaction:
            evidence.append(EvidenceItem("Transaction", transaction.transaction_id, _transaction_payload(transaction)))
            for finding in db.query(ControlFinding).filter_by(record_type="Transaction", record_id=transaction_id).all():
                evidence.append(EvidenceItem("ControlFinding", finding.finding_id, {"control_id": finding.control_id, "severity": finding.severity, "status": finding.status, "explanation": finding.explanation, "evidence": finding.evidence}))
            for anomaly in db.query(Anomaly).filter_by(transaction_id=transaction_id).all():
                evidence.append(EvidenceItem("Anomaly", anomaly.anomaly_id, {"risk_score": float(anomaly.risk_score), "severity": anomaly.severity, "anomaly_type": anomaly.anomaly_type, "explanation": anomaly.explanation}))
            related = db.query(Transaction).filter(Transaction.account == transaction.account, Transaction.currency == transaction.currency, Transaction.transaction_id != transaction_id).order_by(Transaction.transaction_date.desc()).limit(5).all()
            for item in related:
                evidence.append(EvidenceItem("RelatedTransaction", item.transaction_id, _transaction_payload(item)))
    # de-duplicate a source collected both as target and related context.
    return list({(item.source_type, item.source_id): item for item in evidence}.values())


def validate_evidence(evidence: list[EvidenceItem]) -> None:
    for item in evidence:
        if not item.source_type or not item.source_id or not isinstance(item.payload, dict):
            raise ValueError("Evidence must have a source type, source ID, and object payload")


def validate_result(result: InvestigationResult) -> None:
    """Reject malformed provider output before it can be persisted or reported."""
    if not isinstance(result, InvestigationResult):
        raise ValueError("Investigation provider returned an invalid result")
    if not 0 <= result.confidence <= 1:
        raise ValueError("Investigation confidence must be between 0 and 1")
    if not all(isinstance(value, str) and value.strip() for value in (result.summary, result.risk_assessment, result.likely_cause, result.recommended_next_action)):
        raise ValueError("Investigation narrative fields must be non-empty strings")
    if not isinstance(result.supporting_evidence, list) or not all(isinstance(item, str) for item in result.supporting_evidence):
        raise ValueError("Investigation supporting evidence must be a list of strings")
    if not isinstance(result.conflicting_evidence, list) or not all(isinstance(item, dict) for item in result.conflicting_evidence):
        raise ValueError("Investigation conflicting evidence must be a list of objects")


def _persist(db: Session, target_type: str, target_id: str, provider: InvestigationProvider, result: InvestigationResult, evidence: list[EvidenceItem]) -> Investigation:
    fingerprint = sha256(f"{target_type}|{target_id}".encode()).hexdigest()
    investigation = db.query(Investigation).filter_by(fingerprint=fingerprint).one_or_none()
    now = datetime.now(UTC).replace(tzinfo=None)
    values = {"provider": provider.name, "summary": result.summary, "risk_assessment": result.risk_assessment, "likely_cause": result.likely_cause, "conflicting_evidence": result.conflicting_evidence, "confidence": result.confidence, "recommended_next_action": result.recommended_next_action, "updated_at": now}
    if investigation is None:
        investigation = Investigation(investigation_id=f"INV-{uuid4().hex[:16].upper()}", fingerprint=fingerprint, target_type=target_type, target_id=target_id, status="REVIEW_REQUIRED", created_at=now, **values)
        db.add(investigation); db.flush()
    else:
        for key, value in values.items(): setattr(investigation, key, value)
        db.query(InvestigationEvidence).filter_by(investigation_id=investigation.investigation_id).delete(synchronize_session=False)
    for item in evidence:
        db.add(InvestigationEvidence(investigation_id=investigation.investigation_id, source_type=item.source_type, source_id=item.source_id, payload=item.payload))
    return investigation


def serialize_investigation(item: Investigation, evidence: list[InvestigationEvidence] | None = None) -> dict[str, Any]:
    result = {"investigation_id": item.investigation_id, "target_type": item.target_type, "target_id": item.target_id, "status": item.status, "provider": item.provider, "summary": item.summary, "risk_assessment": item.risk_assessment, "likely_cause": item.likely_cause, "conflicting_evidence": item.conflicting_evidence, "confidence": float(item.confidence), "recommended_next_action": item.recommended_next_action, "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()}
    if evidence is not None: result["evidence"] = [{"source_type": x.source_type, "source_id": x.source_id, "payload": x.payload} for x in evidence]
    return result


def investigate(db: Session, target_type: str, target_id: str, provider: InvestigationProvider | None = None) -> dict[str, Any] | None:
    try:
        evidence = collect_evidence(db, target_type, target_id)
        if not evidence: return None
        validate_evidence(evidence)
        selected = provider or get_provider()
        result = selected.investigate(target_type, target_id, evidence, ANTI_HALLUCINATION_INSTRUCTIONS)
        validate_result(result)
        item = _persist(db, target_type, target_id, selected, result, evidence)
        db.commit()
        stored = db.query(InvestigationEvidence).filter_by(investigation_id=item.investigation_id).all()
        return serialize_investigation(item, stored)
    except Exception:
        db.rollback(); logger.exception("RazInvestigate failed for %s:%s", target_type, target_id); raise


def get_investigations(db: Session, limit: int | None = None) -> list[dict[str, Any]]:
    query = db.query(Investigation).order_by(Investigation.updated_at.desc())
    if limit is not None:
        query = query.limit(limit)
    return [serialize_investigation(item) for item in query.all()]


def get_investigation(db: Session, investigation_id: str) -> dict[str, Any] | None:
    item = db.query(Investigation).filter_by(investigation_id=investigation_id).one_or_none()
    if item is None: return None
    return serialize_investigation(item, db.query(InvestigationEvidence).filter_by(investigation_id=investigation_id).all())


def update_investigation_status(db: Session, investigation_id: str, status: str) -> dict[str, Any] | None:
    if status not in {"OPEN", "INVESTIGATING", "REVIEW_REQUIRED", "RESOLVED"}: raise ValueError("invalid investigation status")
    item = db.query(Investigation).filter_by(investigation_id=investigation_id).one_or_none()
    if item is None: return None
    item.status = status; item.updated_at = datetime.now(UTC).replace(tzinfo=None); db.commit()
    return serialize_investigation(item)
