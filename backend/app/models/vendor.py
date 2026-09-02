from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    vendor_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    tax_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        default="India",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )