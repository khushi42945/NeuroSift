from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Credentials(APIModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("password")
    @classmethod
    def bcrypt_byte_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be no longer than 72 UTF-8 bytes")
        return value


class AuthResponse(APIModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    is_guest: bool


class UserResponse(APIModel):
    id: int
    email: str | None
    is_guest: bool


class AnalyzeEntryRequest(APIModel):
    text: str = Field(min_length=1, max_length=4000)
    mood_tag: str | None = Field(default=None, max_length=32)

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Journal text cannot be blank")
        return value.strip()


class AssessmentRequest(APIModel):
    assessment_type: Literal["PHQ-9", "GAD-7"]
    answers: list[int] = Field(min_length=7, max_length=9)

    @field_validator("answers")
    @classmethod
    def answers_in_range(cls, value: list[int]) -> list[int]:
        if any(answer not in (0, 1, 2, 3) for answer in value):
            raise ValueError("Each answer must be from 0 to 3")
        return value

    @model_validator(mode="after")
    def expected_answer_count(self):
        expected = 9 if self.assessment_type == "PHQ-9" else 7
        if len(self.answers) != expected:
            raise ValueError(f"{self.assessment_type} requires exactly {expected} answers")
        return self


class DailyLogResponse(APIModel):
    id: int
    entry_date: date
    mood_tag: str | None
    sentiment_score: float
    dominant_emotion: str


class TrendPoint(APIModel):
    date: date
    sentiment_score: float | None
    mood_score: float | None
    stress_score: float | None
    moving_average: float | None
    entry_count: int


class TrendSummary(APIModel):
    points: list[TrendPoint]
    trend: Literal["improving", "steady", "declining", "insufficient_data"]
    risk_level: Literal["Green", "Amber"]
    summary: str


class ChatTurn(APIModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(APIModel):
    messages: list[ChatTurn] = Field(min_length=1, max_length=24)
    request_summary: bool = False
    session_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def latest_message_is_from_user(self):
        if self.messages[-1].role != "user":
            raise ValueError("The latest conversation message must be from the user")
        if sum(len(message.content) for message in self.messages) > 12000:
            raise ValueError("Conversation context is too long")
        return self


class ConversationProfile(APIModel):
    primary_issue: Literal["trauma", "sleep", "academic_stress", "burnout", "anxiety", "low_mood", "general", "crisis_support"]
    severity: Literal["low", "mild", "moderate", "high"]
    keywords: list[str]
    dominant_emotion: str
    crisis_flag: bool


class DoctorRecommendationRequest(APIModel):
    primary_issue: str = Field(default="general", max_length=64)
    severity: Literal["low", "mild", "moderate", "high"] = "low"
    keywords: list[str] = Field(default_factory=list, max_length=12)
    specialty: str | None = Field(default=None, max_length=80)
    min_experience: int = Field(default=0, ge=0, le=60)
    session_mode: Literal["online", "in_person"] | None = None
    language: str | None = Field(default=None, max_length=40)
    min_rating: float = Field(default=0, ge=0, le=5)


class DoctorProfileResponse(APIModel):
    id: int
    display_name: str
    credentials: str
    headline: str
    specialties: list[str]
    focus_areas: list[str]
    years_experience: int
    session_fee_inr: int
    languages: list[str]
    session_modes: list[str]
    rating: float
    review_count: int
    bio: str
    booking_url: str | None
    is_verified: bool
    is_demo: bool
    match_reasons: list[str]


class DoctorRecommendationResponse(APIModel):
    doctors: list[DoctorProfileResponse]
    safety_first: bool
    note: str