import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


class Artisan(Base):
    __tablename__ = "artisans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    trade: Mapped[str] = mapped_column(String(64), index=True)
    location: Mapped[dict] = mapped_column(JSON)
    language_preference: Mapped[str] = mapped_column(String(12), default="mr")
    profile_draft: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    description_raw: Mapped[str] = mapped_column(Text)
    location: Mapped[dict] = mapped_column(JSON)
    trade_inferred: Mapped[str] = mapped_column(String(64), index=True)
    service_key: Mapped[str] = mapped_column(String(100))
    urgency_score: Mapped[str] = mapped_column(String(16))
    price_band_min_inr: Mapped[int] = mapped_column(Integer)
    price_band_max_inr: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    assigned_artisan_id: Mapped[str | None] = mapped_column(
        ForeignKey("artisans.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobDecline(Base):
    __tablename__ = "job_declines"

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    artisan_id: Mapped[str] = mapped_column(ForeignKey("artisans.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    artisan_id: Mapped[str] = mapped_column(ForeignKey("artisans.id"), index=True)
    agreed_price_inr: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending_acceptance", index=True)
    payment_status: Mapped[str] = mapped_column(String(16), default="held", index=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
