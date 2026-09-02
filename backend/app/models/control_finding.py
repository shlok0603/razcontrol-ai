from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ControlFinding(Base):
    __tablename__ = "control_findings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    finding_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    control_id: Mapped[str] = mapped_column(String(100), index=True)
    record_type: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )
