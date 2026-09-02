from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    bank_transaction_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    transaction_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    transaction_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
    )

    reconciliation_status: Mapped[str] = mapped_column(
        String(50),
        default="UNMATCHED",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )