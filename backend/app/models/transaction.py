from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    transaction_id: Mapped[str] = mapped_column(
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

    vendor: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    account: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
    )

    transaction_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )