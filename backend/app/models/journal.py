from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    journal_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    debit_account: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    credit_account: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING_APPROVAL",
        nullable=False,
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        default="RazJournal",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )