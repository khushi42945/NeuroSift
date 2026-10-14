from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.concurrency import run_in_threadpool
from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_engine import GAD7_QUESTIONS, PHQ9_LABELS, PHQ9_QUESTIONS, analyze_text, score_assessment
from auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from database import get_db, init_db
from conversation_engine import build_chat_reply, extract_conversation_profile, generate_assistant_message
from models import Assessment, DailyLog, RiskAlert, TherapistProfile, User, utc_now, validate_encryption_key
from seed_data import seed_demo_profiles
from schemas import (
    AnalyzeEntryRequest,
    AssessmentRequest,
    AuthResponse,
    ChatRequest,
    ConversationProfile,
    Credentials,
    DailyLogResponse,
    DoctorRecommendationRequest,
    DoctorRecommendationResponse,
    DoctorProfileResponse,
    TrendPoint,
    TrendSummary,
    UserResponse,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        validate_encryption_key()
    auto_create_default = "false" if os.getenv("ENVIRONMENT", "development").lower() == "production" else "true"
    if os.getenv("AUTO_CREATE_SCHEMA", auto_create_default).lower() in {"1", "true", "yes"}:
        init_db()
        if os.getenv("ENVIRONMENT", "development").lower() != "production":
            from database import SessionLocal

            with SessionLocal() as db:
                seed_demo_profiles(db)
    yield


app = FastAPI(
    title="MindPulse API",
    version="1.0.0",
    description="Private wellness reflection and screening tools. Not a diagnostic service.",
    lifespan=lifespan,
)
origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user, user.guest_uuid), is_guest=user.is_guest)


def _create_alert(db: Session, user: User, level: str, reason: str) -> RiskAlert:
    alert = RiskAlert(user_id=user.id, alert_level=level, trigger_reason=reason)
    db.add(alert)
    return alert


def _doctor_match_reasons(doctor: TherapistProfile, issue: str, keywords: list[str]) -> list[str]:
    profile_tags = " ".join([*doctor.specialties, *doctor.focus_areas]).lower().replace(" ", "_")
    reasons = []
    if issue != "general" and issue.replace("_", " ") in " ".join(doctor.specialties).lower():
        reasons.append(f"Focus on {issue.replace('_', ' ')}")
    for keyword in keywords:
        normalized = keyword.lower().replace(" ", "_")
        if normalized in profile_tags and len(reasons) < 3:
            reasons.append(f"Experience with {keyword.replace('_', ' ')}")
    if not reasons:
        reasons.append("Offers support for young adults")
    return reasons


@app.get("/health")
def health():
    return {"status": "ok", "service": "mindpulse-api"}


@app.post("/api/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: Credentials, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=payload.email, hashed_password=hash_password(payload.password), is_guest=False)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    db.refresh(user)
    return _auth_response(user)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email, User.is_guest.is_(False)))
    if user is None or user.hashed_password is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _auth_response(user)


@app.post("/api/auth/guest", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def create_guest(db: Session = Depends(get_db)):
    guest_uuid = str(uuid.uuid4())
    user = User(is_guest=True, guest_uuid=guest_uuid)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(user)


@app.get("/api/auth/google")
def google_login():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    state = jwt.encode(
        {"purpose": "google_oauth_state", "nonce": str(uuid.uuid4()), "exp": utc_now() + timedelta(minutes=10)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


@app.get("/api/auth/google/callback")
async def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    try:
        state_payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
        if state_payload.get("purpose") != "google_oauth_state":
            raise ValueError("Invalid OAuth state")
    except (JWTError, ValueError):
        raise HTTPException(status_code=400, detail="Google sign-in state is invalid or expired")

    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_response.is_error:
            raise HTTPException(status_code=401, detail="Google sign-in could not be verified")
        identity_response = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token_response.json().get("id_token", "")},
        )
    identity = identity_response.json() if identity_response.is_success else {}
    email = identity.get("email", "").strip().lower()
    if identity.get("aud") != client_id or identity.get("email_verified") not in (True, "true") or "@" not in email:
        raise HTTPException(status_code=401, detail="Google account identity could not be verified")

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, is_guest=False)
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(user)
    return RedirectResponse(f"{frontend_url}/auth/callback#token={token}")


@app.get("/api/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user


@app.delete("/api/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()


@app.post("/api/analyze-entry")
async def analyze_entry(
    payload: AnalyzeEntryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    analysis = await run_in_threadpool(analyze_text, payload.text)
    log = DailyLog(
        user_id=user.id,
        entry_date=utc_now().date(),
        journal_text=payload.text,
        mood_tag=payload.mood_tag,
        sentiment_score=analysis["sentiment_score"],
        dominant_emotion=analysis["dominant_emotion"],
    )
    db.add(log)
    if analysis["crisis_flag"]:
        _create_alert(db, user, "Red", "Distress language was detected in a journal check-in.")
    db.commit()
    db.refresh(log)
    return {
        "id": log.id,
        **analysis,
        "safety_resources_recommended": analysis["crisis_flag"],
        "recommendations": (
            ["Try the 5-4-3-2-1 grounding exercise", "Reach out to someone you trust", "View immediate support options"]
            if analysis["crisis_flag"]
            else ["Take a few slow breaths", "Consider a short break or gentle movement", "Check in with someone you trust"]
        ),
    }


@app.post("/api/chat")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user_messages = [message.content for message in payload.messages if message.role == "user"]
    profile_data = await run_in_threadpool(extract_conversation_profile, user_messages)
    reply = build_chat_reply(profile_data, len(user_messages), payload.request_summary, user_messages[-1])
    assistant_message, reply_source, processing_notice = await generate_assistant_message(
        [message.model_dump() for message in payload.messages],
        reply["assistant_message"],
        profile_data["crisis_flag"],
    )
    if profile_data["crisis_flag"]:
        existing = db.scalar(
            select(RiskAlert.id).where(
                RiskAlert.user_id == user.id,
                RiskAlert.alert_level == "Red",
                RiskAlert.resolved_status.is_(False),
                RiskAlert.trigger_reason == "A conversation message included urgent self-harm language.",
            )
        )
        if existing is None:
            _create_alert(db, user, "Red", "A conversation message included urgent self-harm language.")
            db.commit()
    profile = ConversationProfile(**profile_data)
    return {
        "session_id": payload.session_id or str(uuid.uuid4()),
        "assistant_message": assistant_message,
        "wellness_summary": reply["wellness_summary"],
        "recommendation_ready": reply["recommendation_ready"],
        "safety_resources_recommended": reply["safety_resources_recommended"],
        "profile": profile,
        "reply_source": reply_source,
        "processing_notice": processing_notice,
        "disclaimer": "This conversation offers reflection, not diagnosis or emergency monitoring.",
    }


@app.post("/api/doctors/recommend", response_model=DoctorRecommendationResponse)
def recommend_doctors(
    payload: DoctorRecommendationRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if payload.severity == "high":
        return DoctorRecommendationResponse(
            doctors=[],
            safety_first=True,
            note="Immediate human support is more appropriate than routine appointment matching right now. See the crisis resources first.",
        )

    candidates = db.scalars(
        select(TherapistProfile).where(
            (TherapistProfile.is_verified.is_(True)) | (TherapistProfile.is_demo.is_(True)),
            TherapistProfile.years_experience >= payload.min_experience,
            TherapistProfile.rating >= payload.min_rating,
        )
    ).all()
    filtered = []
    for doctor in candidates:
        if payload.session_mode and payload.session_mode not in doctor.session_modes:
            continue
        if payload.language and payload.language.lower() not in [language.lower() for language in doctor.languages]:
            continue
        if payload.specialty and not any(payload.specialty.lower() in item.lower() for item in doctor.specialties):
            continue
        searchable = " ".join([*doctor.specialties, *doctor.focus_areas]).lower().replace(" ", "_")
        issue = payload.primary_issue.lower()
        matched_keywords = [keyword for keyword in payload.keywords if keyword.lower().replace(" ", "_") in searchable]
        issue_match = issue != "general" and issue.replace(" ", "_") in searchable
        match_score = (3 if issue_match else 0) + len(matched_keywords)
        reasons = _doctor_match_reasons(doctor, issue, payload.keywords)
        filtered.append((match_score, doctor.rating, doctor, reasons))

    filtered.sort(key=lambda item: (item[2].is_verified, item[0], item[1], item[2].years_experience), reverse=True)
    profiles = [
        DoctorProfileResponse(
            id=doctor.id,
            display_name=doctor.display_name,
            credentials=doctor.credentials,
            headline=doctor.headline,
            specialties=doctor.specialties,
            focus_areas=doctor.focus_areas,
            years_experience=doctor.years_experience,
            session_fee_inr=doctor.session_fee_inr,
            languages=doctor.languages,
            session_modes=doctor.session_modes,
            rating=doctor.rating,
            review_count=doctor.review_count,
            bio=doctor.bio,
            booking_url=doctor.booking_url if doctor.is_verified else None,
            is_verified=doctor.is_verified,
            is_demo=doctor.is_demo,
            match_reasons=reasons,
        )
        for _, _, doctor, reasons in filtered[:8]
    ]
    demo_only = bool(profiles) and all(doctor.is_demo for doctor in profiles)
    note = (
        "Demo directory: these sample profiles, ratings, credentials, and fees are fictional and unverified. Booking is disabled."
        if demo_only
        else "Recommendations are based on conversation topics, not a diagnosis. Verify a provider's credentials before booking."
    )
    return DoctorRecommendationResponse(doctors=profiles, safety_first=False, note=note)


@app.get("/api/logs", response_model=list[DailyLogResponse])
def get_logs(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list(
        db.scalars(
            select(DailyLog).where(DailyLog.user_id == user.id).order_by(DailyLog.entry_date.desc(), DailyLog.id.desc()).limit(limit)
        ).all()
    )


@app.get("/api/assess/questions")
def assessment_questions(assessment_type: str = Query(pattern="^(PHQ-9|GAD-7)$")):
    questions = PHQ9_QUESTIONS if assessment_type == "PHQ-9" else GAD7_QUESTIONS
    return {"assessment_type": assessment_type, "questions": questions, "options": PHQ9_LABELS}


@app.post("/api/assess/{assessment_type}")
def submit_assessment(
    assessment_type: str,
    payload: AssessmentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    path_type = assessment_type.lower().replace("-", "")
    normalized_type = {"phq9": "PHQ-9", "gad7": "GAD-7"}.get(path_type)
    if normalized_type != payload.assessment_type:
        raise HTTPException(status_code=422, detail="Assessment type in path and body must match")
    try:
        result = score_assessment(payload.assessment_type, payload.answers)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    assessment = Assessment(
        user_id=user.id,
        assessment_type=result["assessment_type"],
        answers=payload.answers,
        total_score=result["total_score"],
        severity_category=result["severity_category"],
    )
    db.add(assessment)
    if result["crisis_flag"]:
        _create_alert(db, user, "Red", "A positive response to PHQ-9 item 9 needs a timely, human follow-up.")
    elif result["total_score"] >= 10:
        _create_alert(db, user, "Amber", f"Elevated {result['assessment_type']} screening score.")
    db.commit()
    db.refresh(assessment)
    return {
        **result,
        "id": assessment.id,
        "timestamp": assessment.timestamp,
        "support_resources_recommended": result["crisis_flag"] or result["severity_category"] in ("Severe", "Moderately Severe"),
        "disclaimer": "A screening score is not a diagnosis. A qualified professional can help interpret it in context.",
    }


@app.get("/api/trends/summary", response_model=TrendSummary)
def trends_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = utc_now().date()
    start_date = today - timedelta(days=6)
    rows = db.execute(
        select(
            DailyLog.entry_date,
            func.avg(DailyLog.sentiment_score),
            func.count(DailyLog.id),
        )
        .where(DailyLog.user_id == user.id, DailyLog.entry_date >= start_date, DailyLog.entry_date <= today)
        .group_by(DailyLog.entry_date)
        .order_by(DailyLog.entry_date)
    ).all()
    by_date = {row[0]: (float(row[1]), int(row[2])) for row in rows}
    assessment_rows = db.execute(
        select(Assessment.timestamp, Assessment.total_score)
        .where(
            Assessment.user_id == user.id,
            Assessment.assessment_type == "GAD-7",
            Assessment.timestamp >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc),
            Assessment.timestamp < datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc),
        )
        .order_by(Assessment.timestamp)
    ).all()
    stress_by_date = {}
    for timestamp, total_score in assessment_rows:
        stress_by_date[timestamp.date()] = round(total_score / 21 * 100, 1)
    points = []
    observed = []
    for offset in range(7):
        point_date = start_date + timedelta(days=offset)
        sentiment, entry_count = by_date[point_date] if point_date in by_date else (None, 0)
        if sentiment is not None:
            observed.append(sentiment)
        trailing = observed[-7:]
        points.append(
            TrendPoint(
                date=point_date,
                sentiment_score=round(sentiment, 3) if sentiment is not None else None,
                mood_score=round((sentiment + 1) * 50, 1) if sentiment is not None else None,
                stress_score=stress_by_date.get(point_date),
                moving_average=round(sum(trailing) / len(trailing), 3) if trailing else None,
                entry_count=entry_count,
            )
        )
    if len(observed) < 3:
        trend = "insufficient_data"
        risk_level = "Green"
        summary = "Keep checking in to build a useful picture of your week. This is not a clinical risk assessment."
    else:
        change = observed[-1] - observed[0]
        if change <= -0.25:
            trend = "declining"
        elif change >= 0.25:
            trend = "improving"
        else:
            trend = "steady"
        risk_level = "Amber" if trend == "declining" and sum(observed[-3:]) / min(3, len(observed)) < -0.15 else "Green"
        summary = (
            "Your recent check-ins have shifted lower. Consider reaching out to someone you trust or a qualified professional."
            if risk_level == "Amber"
            else "Your check-ins look relatively steady. Keep noticing what supports your well-being."
            if trend == "steady"
            else "Your recent check-ins have been trending upward. Keep noting what has been helping."
            if trend == "improving"
            else "Your mood check-ins have shifted over the week. A few more entries can clarify the pattern."
        )
    return TrendSummary(points=points, trend=trend, risk_level=risk_level, summary=summary)


@app.get("/api/risk-alerts")
def get_risk_alerts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alerts = db.scalars(
        select(RiskAlert)
        .where(RiskAlert.user_id == user.id, RiskAlert.resolved_status.is_(False))
        .order_by(RiskAlert.created_at.desc())
        .limit(20)
    ).all()
    return [
        {
            "id": alert.id,
            "alert_level": alert.alert_level,
            "trigger_reason": alert.trigger_reason,
            "created_at": alert.created_at,
        }
        for alert in alerts
    ]


@app.post("/api/risk-alerts/{alert_id}/resolve", status_code=status.HTTP_204_NO_CONTENT)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    alert = db.scalar(select(RiskAlert).where(RiskAlert.id == alert_id, RiskAlert.user_id == user.id))
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved_status = True
    db.commit()