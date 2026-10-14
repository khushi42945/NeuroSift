from __future__ import annotations

import base64
import hashlib
import os
from datetime import date, datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _journal_cipher() -> Fernet:
    configured_key = os.getenv("FIELD_ENCRYPTION_KEY")
    if configured_key:
        return Fernet(configured_key.encode())
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise RuntimeError("Set a stable FIELD_ENCRYPTION_KEY before running in production")
    secret = os.getenv("SECRET_KEY", "insecure-development-key-change-me")
    derived_key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(derived_key)


def validate_encryption_key() -> None:
    _journal_cipher()


class EncryptedText(TypeDecorator):
    """Fernet-encrypt journal content in the database; decrypt on ORM reads."""

    impl = Text
    cache_ok = False

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _journal_cipher().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return _journal_cipher().decrypt(value.encode()).decode()
        except Exception as error:
            raise ValueError("Journal encryption key is invalid or has changed") from error


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    guest_uuid: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    daily_logs: Mapped[list["DailyLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    risk_alerts: Mapped[list["RiskAlert"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class DailyLog(Base):
    __tablename__ = "daily_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, default=lambda: utc_now().date(), index=True, nullable=False)
    journal_text: Mapped[str] = mapped_column(EncryptedText(), nullable=False)
    mood_tag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    dominant_emotion: Mapped[str] = mapped_column(String(32), nullable=False)

    user: Mapped[User] = relationship(back_populates="daily_logs")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(8), nullable=False)
    answers: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    severity_category: Mapped[str] = mapped_column(String(24), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="assessments")


class RiskAlert(Base):
    __tablename__ = "risk_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    alert_level: Mapped[str] = mapped_column(String(8), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    resolved_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="risk_alerts")


class TherapistProfile(Base):
    __tablename__ = "therapist_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    credentials: Mapped[str] = mapped_column(String(180), nullable=False)
    headline: Mapped[str] = mapped_column(String(180), nullable=False)
    specialties: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    focus_areas: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False)
    session_fee_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    languages: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    session_modes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False)
    bio: Mapped[str] = mapped_column(String(600), nullable=False)
    booking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)