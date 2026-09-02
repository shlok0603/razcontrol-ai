from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    invoice_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    vendor_code: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    invoice_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    due_date: Mapped[date | None] = mapped_column(
        Date,
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

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="OPEN",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )