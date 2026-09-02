from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ReconciliationMatch(Base):
    __tablename__ = "reconciliation_matches"

    # REVIEW records are candidates, not reservations. Only automatic
    # MATCHED results require one-to-one database enforcement.
    __table_args__ = (
        Index(
            "uq_reconciliation_matches_matched_transaction",
            "transaction_id",
            unique=True,
            postgresql_where=text("status = 'MATCHED'"),
            sqlite_where=text("status = 'MATCHED'"),
        ),
    )

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

    transaction_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    amount_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    date_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    description_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    matched_by: Mapped[str] = mapped_column(
        String(100),
        default="RazRecon",
        nullable=False,
    )

    matched_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )
