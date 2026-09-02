from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        default="India",
        nullable=False,
    )

    base_currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
    )

    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )