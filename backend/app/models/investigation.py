from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investigation_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    target_type: Mapped[str] = mapped_column(String(50), index=True)
    target_id: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    risk_assessment: Mapped[str] = mapped_column(Text, nullable=False)
    likely_cause: Mapped[str] = mapped_column(Text, nullable=False)
    conflicting_evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    recommended_next_action: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)


class InvestigationEvidence(Base):
    __tablename__ = "investigation_evidence"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investigation_id: Mapped[str] = mapped_column(String(100), index=True)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)
