from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anomaly_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    anomaly_type: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False)
    detected_by: Mapped[str] = mapped_column(String(100), nullable=False)
    detection_method: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)
