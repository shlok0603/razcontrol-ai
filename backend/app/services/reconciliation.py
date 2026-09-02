from datetime import UTC, datetime, timedelta
from decimal import Decimal

from rapidfuzz.fuzz import ratio
from sqlalchemy.orm import Session

from app.models import (
    Transaction,
    BankTransaction,
    ReconciliationMatch,
)


# ============================================================
# MATCHING WEIGHTS
# ============================================================

AMOUNT_WEIGHT = 0.50
DATE_WEIGHT = 0.20
DESCRIPTION_WEIGHT = 0.30


# ============================================================
# AMOUNT SIMILARITY
# ============================================================

def amount_similarity(
    bank_amount: Decimal,
    gl_amount: Decimal,
) -> float:

    if bank_amount == gl_amount:
        return 1.0

    if bank_amount == 0 or gl_amount == 0:
        return 0.0

    difference = abs(
        bank_amount - gl_amount
    )

    average = (
        abs(bank_amount)
        + abs(gl_amount)
    ) / Decimal("2")

    similarity = 1 - (
        difference / average
    )

    return max(
        0.0,
        float(similarity),
    )


# ============================================================
# DATE SIMILARITY
# ============================================================

def date_similarity(
    bank_date,
    gl_date,
) -> float:

    difference = abs(
        bank_date - gl_date
    )

    days = difference.days

    if days == 0:
        return 1.0

    if days == 1:
        return 0.8

    if days == 2:
        return 0.6

    if days <= 5:
        return 0.3

    return 0.0


# ============================================================
# DESCRIPTION SIMILARITY
# ============================================================

def description_similarity(
    bank_description: str,
    gl_description: str,
) -> float:

    if not bank_description or not gl_description:
        return 0.0

    score = ratio(
        bank_description.lower(),
        gl_description.lower(),
    )

    return score / 100.0


# ============================================================
# CALCULATE MATCH SCORES
# ============================================================

def calculate_match_scores(
    bank_transaction: BankTransaction,
    gl_transaction: Transaction,
):
    """
    Calculates individual matching factors and
    the final reconciliation confidence.
    """

    amount_score = amount_similarity(
        bank_transaction.amount,
        gl_transaction.amount,
    )

    date_score = date_similarity(
        bank_transaction.transaction_date,
        gl_transaction.transaction_date,
    )

    description_score = description_similarity(
        bank_transaction.description,
        gl_transaction.description,
    )

    confidence = (
        amount_score * AMOUNT_WEIGHT
        + date_score * DATE_WEIGHT
        + description_score * DESCRIPTION_WEIGHT
    )

    return {
        "amount_score": round(
            amount_score * 100,
            2,
        ),
        "date_score": round(
            date_score * 100,
            2,
        ),
        "description_score": round(
            description_score * 100,
            2,
        ),
        "confidence": round(
            confidence * 100,
            2,
        ),
    }


# ============================================================
# FIND BEST MATCH
# ============================================================

def find_best_match(
    db: Session,
    bank_transaction: BankTransaction,
    used_transaction_ids: set[str],
):
    """
    Finds the best AVAILABLE GL transaction.

    Both previously persisted matches and matches
    created during the current run are excluded.
    """

    start_date = (
        bank_transaction.transaction_date
        - timedelta(days=5)
    )

    end_date = (
        bank_transaction.transaction_date
        + timedelta(days=5)
    )

    candidates = (
        db.query(Transaction)
        .filter(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .all()
    )

    best_match = None
    best_scores = None

    for candidate in candidates:

        # Enforce one-to-one matching.
        if candidate.transaction_id in used_transaction_ids:
            continue

        scores = calculate_match_scores(
            bank_transaction,
            candidate,
        )

        if (
            best_scores is None
            or scores["confidence"]
            > best_scores["confidence"]
        ):
            best_match = candidate
            best_scores = scores

    return best_match, best_scores


# ============================================================
# BUILD HUMAN-READABLE REASON
# ============================================================

def build_reason(scores: dict) -> str:

    reasons = []

    if scores["amount_score"] == 100:
        reasons.append(
            "exact amount match"
        )

    elif scores["amount_score"] >= 95:
        reasons.append(
            "very close amount"
        )

    if scores["date_score"] == 100:
        reasons.append(
            "same transaction date"
        )

    elif scores["date_score"] >= 80:
        reasons.append(
            "nearby transaction date"
        )

    if scores["description_score"] >= 90:
        reasons.append(
            "highly similar descriptions"
        )

    elif scores["description_score"] >= 70:
        reasons.append(
            "similar descriptions"
        )

    if not reasons:
        return (
            "Weak similarity across available "
            "transaction fields"
        )

    return ", ".join(reasons)


# ============================================================
# RECONCILE ONE BANK TRANSACTION
# ============================================================

def reconcile_bank_transaction(
    db: Session,
    bank_transaction: BankTransaction,
    used_transaction_ids: set[str],
):
    """
    Reconciles one bank transaction against GL.

    Possible outcomes:

        MATCHED
        REVIEW
        UNMATCHED

    Every decision is persisted as the single current result for its bank
    transaction, so reruns refresh stale REVIEW/UNMATCHED results.
    """

    match, scores = find_best_match(
        db,
        bank_transaction,
        used_transaction_ids,
    )

    # ========================================================
    # NO GL CANDIDATE
    # ========================================================

    if match is None:

        bank_transaction.reconciliation_status = (
            "UNMATCHED"
        )

        reason = (
            "No available GL transaction candidate"
        )

        _persist_reconciliation(
            db,
            bank_transaction_id=bank_transaction.bank_transaction_id,
            transaction_id=None,
            confidence=0.0,
            amount_score=0.0,
            date_score=0.0,
            description_score=0.0,
            status="UNMATCHED",
            reason=reason,
        )

        return {
            "status": "UNMATCHED",

            "confidence": 0.0,

            "amount_score": 0.0,

            "date_score": 0.0,

            "description_score": 0.0,

            "bank_transaction_id": (
                bank_transaction.bank_transaction_id
            ),

            "transaction_id": None,

            "reason": reason,
        }

    # ========================================================
    # MATCH FOUND
    # ========================================================

    confidence = scores["confidence"]

    # ========================================================
    # DETERMINE STATUS
    # ========================================================

    if confidence >= 85:

        status = "MATCHED"

    elif confidence >= 60:

        status = "REVIEW"

    else:

        status = "UNMATCHED"

    bank_transaction.reconciliation_status = status

    reason = build_reason(scores)

    # ========================================================
    # CREATE PERSISTED RECONCILIATION RECORD
    # ========================================================
    matched_transaction_id = (
        match.transaction_id
        if status in {"MATCHED", "REVIEW"}
        else None
    )
    _persist_reconciliation(
        db,
        bank_transaction_id=bank_transaction.bank_transaction_id,
        transaction_id=matched_transaction_id,
        confidence=confidence,
        amount_score=scores["amount_score"],
        date_score=scores["date_score"],
        description_score=scores["description_score"],
        status=status,
        reason=reason,
    )

    # ========================================================
    # RESERVE GL TRANSACTION
    # ========================================================

    # Only automatic MATCHED transactions are reserved.
    #
    # REVIEW and UNMATCHED transactions do not consume
    # the GL transaction because they haven't been confirmed.
    if status == "MATCHED":

        used_transaction_ids.add(
            match.transaction_id
        )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {
        "status": status,

        "confidence": confidence,

        "amount_score": (
            scores["amount_score"]
        ),

        "date_score": (
            scores["date_score"]
        ),

        "description_score": (
            scores["description_score"]
        ),

        "bank_transaction_id": (
            bank_transaction.bank_transaction_id
        ),

        "transaction_id": matched_transaction_id,

        "reason": reason,
    }


def _persist_reconciliation(
    db: Session,
    *,
    bank_transaction_id: str,
    transaction_id: str | None,
    confidence: float,
    amount_score: float,
    date_score: float,
    description_score: float,
    status: str,
    reason: str,
) -> ReconciliationMatch:
    """Create or refresh the one current result for a bank transaction."""
    reconciliation = (
        db.query(ReconciliationMatch)
        .filter(ReconciliationMatch.bank_transaction_id == bank_transaction_id)
        .one_or_none()
    )
    if reconciliation is None:
        reconciliation = ReconciliationMatch(
            bank_transaction_id=bank_transaction_id,
            matched_by="RazRecon",
        )
        db.add(reconciliation)

    reconciliation.transaction_id = transaction_id
    reconciliation.confidence = confidence
    reconciliation.amount_score = amount_score
    reconciliation.date_score = date_score
    reconciliation.description_score = description_score
    reconciliation.status = status
    reconciliation.reason = reason
    reconciliation.matched_by = "RazRecon"
    reconciliation.matched_at = datetime.now(UTC).replace(tzinfo=None)
    return reconciliation


# ============================================================
# RECONCILE ALL BANK TRANSACTIONS
# ============================================================

def reconcile_all(
    db: Session,
):
    """
    Reconciles bank transactions that are not already automatically MATCHED.

    Enforces one-to-one matching across the
    entire reconciliation run.
    """

    bank_transactions = (
        db.query(BankTransaction)
        .filter(BankTransaction.reconciliation_status != "MATCHED")
        .order_by(BankTransaction.transaction_date, BankTransaction.id)
        .all()
    )

    # ========================================================
    # LOAD PREVIOUSLY MATCHED GL TRANSACTIONS
    # ========================================================

    used_transaction_ids = {
        row[0]
        for row in (
            db.query(
                ReconciliationMatch.transaction_id
            )
            .join(
                BankTransaction,
                ReconciliationMatch.bank_transaction_id
                == BankTransaction.bank_transaction_id,
            )
            .filter(
                ReconciliationMatch.status
                == "MATCHED"
            )
            .filter(
                BankTransaction.reconciliation_status
                == "MATCHED"
            )
            .filter(
                ReconciliationMatch.transaction_id
                .isnot(None)
            )
            .all()
        )
    }

    # ========================================================
    # PROCESS TRANSACTIONS
    # ========================================================

    results = []

    for bank_transaction in bank_transactions:

        result = reconcile_bank_transaction(
            db,
            bank_transaction,
            used_transaction_ids,
        )

        results.append(result)

    # ========================================================
    # SAVE EVERYTHING
    # ========================================================

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return results


def get_reconciliation_results(db: Session, limit: int | None = None) -> list[dict]:
    """Return persisted reconciliation outcomes for the dashboard/API."""
    query = (
        db.query(ReconciliationMatch)
        .order_by(ReconciliationMatch.matched_at.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    records = query.all()
    return [
        {
            "bank_transaction_id": record.bank_transaction_id,
            "transaction_id": record.transaction_id,
            "status": record.status,
            "confidence": float(record.confidence),
            "amount_score": float(record.amount_score),
            "date_score": float(record.date_score),
            "description_score": float(record.description_score),
            "reason": record.reason,
            "matched_at": record.matched_at.isoformat(),
        }
        for record in records
    ]
