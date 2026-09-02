import random
import uuid
from datetime import timedelta
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Invoice,
    Transaction,
    BankTransaction,
)


def inject_duplicate_invoices(
    db: Session,
    count: int = 20,
):
    """
    Creates duplicate invoices by copying existing invoices
    with slightly modified invoice numbers.
    """

    invoices = (
        db.query(Invoice)
        .limit(count)
        .all()
    )

    injected = []

    for invoice in invoices:

        duplicate = Invoice(
            invoice_number=(
                f"{invoice.invoice_number}-DUP"
            ),

            vendor_code=invoice.vendor_code,

            invoice_date=invoice.invoice_date,

            due_date=invoice.due_date,

            amount=invoice.amount,

            currency=invoice.currency,

            description=invoice.description,

            status="OPEN",
        )

        db.add(duplicate)

        injected.append({
            "type": "DUPLICATE_INVOICE",
            "original_invoice": invoice.invoice_number,
            "duplicate_invoice": duplicate.invoice_number,
            "amount": float(invoice.amount),
            "vendor_code": invoice.vendor_code,
        })

    db.flush()

    return injected


def inject_suspicious_payments(
    db: Session,
    count: int = 20,
):
    """
    Creates unusually large transactions.
    """

    transactions = (
        db.query(Transaction)
        .limit(count)
        .all()
    )

    injected = []

    for transaction in transactions:

        original_amount = transaction.amount

        suspicious_amount = (
            original_amount * Decimal("15")
        )

        transaction.amount = suspicious_amount

        transaction.description = (
            transaction.description
            + " [SUSPICIOUS]"
        )

        injected.append({
            "type": "SUSPICIOUS_PAYMENT",
            "transaction_id": transaction.transaction_id,
            "original_amount": float(
                original_amount
            ),
            "new_amount": float(
                suspicious_amount
            ),
        })

    db.flush()

    return injected


def inject_unmatched_bank_transactions(
    db: Session,
    count: int = 20,
):
    """
    Creates bank transactions that have
    no corresponding GL transaction.
    """

    injected = []

    for _ in range(count):

        bank_transaction = BankTransaction(
            bank_transaction_id=(
                f"ANOM-{uuid.uuid4().hex[:12].upper()}"
            ),

            transaction_date=date.today(),

            description="Unknown payment - investigation required",

            reference=None,

            amount=Decimal(
                str(
                    random.randint(
                        100000,
                        1000000,
                    )
                )
            ),

            transaction_type="DEBIT",

            currency="INR",

            reconciliation_status="UNMATCHED",
        )

        db.add(bank_transaction)

        injected.append({
            "type": "UNMATCHED_BANK_TRANSACTION",
            "bank_transaction_id": (
                bank_transaction.bank_transaction_id
            ),
            "amount": float(
                bank_transaction.amount
            ),
        })

    db.flush()

    return injected


def inject_abnormal_transactions(
    db: Session,
    count: int = 20,
):
    """
    Creates transactions with abnormal amounts
    compared to typical transaction values.
    """

    transactions = (
        db.query(Transaction)
        .offset(100)
        .limit(count)
        .all()
    )

    injected = []

    for transaction in transactions:

        original_amount = transaction.amount

        abnormal_amount = (
            original_amount * Decimal("25")
        )

        transaction.amount = abnormal_amount

        transaction.description = (
            transaction.description
            + " [ABNORMAL_AMOUNT]"
        )

        injected.append({
            "type": "ABNORMAL_AMOUNT",
            "transaction_id": transaction.transaction_id,
            "original_amount": float(
                original_amount
            ),
            "new_amount": float(
                abnormal_amount
            ),
        })

    db.flush()

    return injected


def inject_all_anomalies(
    db: Session,
):
    """
    Inject all development anomalies.
    """

    results = []

    print("Injecting duplicate invoices...")

    results.extend(
        inject_duplicate_invoices(
            db,
            count=20,
        )
    )

    print("Injecting suspicious payments...")

    results.extend(
        inject_suspicious_payments(
            db,
            count=20,
        )
    )

    print("Injecting unmatched bank transactions...")

    results.extend(
        inject_unmatched_bank_transactions(
            db,
            count=20,
        )
    )

    print("Injecting abnormal transactions...")

    results.extend(
        inject_abnormal_transactions(
            db,
            count=20,
        )
    )

    return results