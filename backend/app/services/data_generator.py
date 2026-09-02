import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Company,
    Vendor,
    Transaction,
    BankTransaction,
    Invoice,
)


VENDOR_NAMES = [
    "ABC Technologies",
    "Global Solutions",
    "Prime Consulting",
    "Nova Systems",
    "Bright Logistics",
    "Vertex Enterprises",
    "BlueSky Services",
    "Apex Digital",
    "Zenith Supplies",
    "Orbit Technologies",
    "NextGen Solutions",
    "Matrix Consulting",
    "GreenLeaf Industries",
    "Rapid Logistics",
    "Core Systems",
]


EXPENSE_CATEGORIES = [
    "Office Supplies",
    "Software",
    "Travel",
    "Marketing",
    "Utilities",
    "Professional Services",
    "Logistics",
    "Equipment",
    "Maintenance",
    "Cloud Services",
]


def random_date(start_date: date, end_date: date) -> date:
    delta = end_date - start_date
    return start_date + timedelta(
        days=random.randint(0, delta.days)
    )


def random_amount(
    minimum: float = 500,
    maximum: float = 500000,
) -> Decimal:

    amount = round(
        random.uniform(minimum, maximum),
        2,
    )

    return Decimal(str(amount))


def generate_company(db: Session) -> Company:

    company = Company(
        name="RazTech Industries",
        legal_name="RazTech Industries Private Limited",
        country="India",
        base_currency="INR",
        industry="Technology",
    )

    db.add(company)
    db.flush()

    return company


def generate_vendors(
    db: Session,
    count: int = 100,
):

    vendors = []

    for i in range(count):

        base_name = random.choice(VENDOR_NAMES)

        vendor = Vendor(
            vendor_code=f"VND-{i + 1:05d}",
            name=f"{base_name} {i + 1}",
            tax_id=f"GSTIN{random.randint(100000, 999999)}",
            email=f"vendor{i + 1}@example.com",
            country="India",
        )

        db.add(vendor)
        vendors.append(vendor)

    db.flush()

    return vendors


def generate_transactions(
    db: Session,
    vendors,
    count: int = 10000,
):

    transactions = []

    start_date = date(2025, 9, 1)
    end_date = date(2026, 8, 30)

    for i in range(count):

        vendor = random.choice(vendors)

        amount = random_amount()

        transaction = Transaction(
            transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            transaction_date=random_date(
                start_date,
                end_date,
            ),
            description=f"{random.choice(EXPENSE_CATEGORIES)} expense",
            vendor=vendor.name,
            account=random.choice(EXPENSE_CATEGORIES),
            amount=amount,
            currency="INR",
            transaction_type="DEBIT",
            source="ERP",
        )

        db.add(transaction)
        transactions.append(transaction)

    db.flush()

    return transactions


def generate_invoices(
    db: Session,
    vendors,
    count: int = 3000,
):

    invoices = []

    start_date = date(2025, 9, 1)
    end_date = date(2026, 8, 30)

    for i in range(count):

        vendor = random.choice(vendors)

        invoice_date = random_date(
            start_date,
            end_date,
        )

        due_date = invoice_date + timedelta(days=30)

        invoice = Invoice(
            invoice_number=f"INV-{i + 1:06d}",
            vendor_code=vendor.vendor_code,
            invoice_date=invoice_date,
            due_date=due_date,
            amount=random_amount(),
            currency="INR",
            description=random.choice(
                EXPENSE_CATEGORIES
            ),
            status="OPEN",
        )

        db.add(invoice)
        invoices.append(invoice)

    db.flush()

    return invoices


def generate_bank_transactions(
    db: Session,
    transactions,
    count: int = 5000,
):

    bank_transactions = []

    for i in range(count):

        transaction = random.choice(
            transactions
        )

        bank_transaction = BankTransaction(
            bank_transaction_id=(
                f"BNK-{uuid.uuid4().hex[:12].upper()}"
            ),
            transaction_date=transaction.transaction_date,
            description=transaction.description,
            reference=transaction.transaction_id,
            amount=transaction.amount,
            transaction_type="DEBIT",
            currency="INR",
            reconciliation_status="UNMATCHED",
        )

        db.add(bank_transaction)
        bank_transactions.append(
            bank_transaction
        )

    db.flush()

    return bank_transactions