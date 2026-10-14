from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwe, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User


SECRET_KEY = os.getenv("SECRET_KEY", "insecure-development-key-change-before-deployment")
if os.getenv("ENVIRONMENT", "development").lower() == "production" and (
    len(SECRET_KEY) < 32 or SECRET_KEY.lower().startswith(("insecure-", "development-", "replace-"))
):
    raise RuntimeError("Set a unique SECRET_KEY of at least 32 characters before running in production")
ALGORITHM = "HS256"
ACCESS_TOKEN_HOURS = int(os.getenv("ACCESS_TOKEN_HOURS", "24"))
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_context.verify(password, hashed_password)


def create_access_token(user: User, guest_uuid: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "is_guest": user.is_guest,
        "guest_uuid": guest_uuid,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=2 if user.is_guest else ACCESS_TOKEN_HOURS)).timestamp()),
    }
    if user.is_guest:
        encryption_key = hashlib.sha256(SECRET_KEY.encode()).digest()
        return jwe.encrypt(json.dumps(payload), encryption_key, algorithm="dir", encryption="A256GCM")
    payload["iat"] = now
    payload["exp"] = now + timedelta(hours=ACCESS_TOKEN_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sign in to continue",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized
    try:
        if token.count(".") == 4:
            encryption_key = hashlib.sha256(SECRET_KEY.encode()).digest()
            payload = json.loads(jwe.decrypt(token, encryption_key))
        else:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if int(payload.get("exp", 0)) <= datetime.now(timezone.utc).timestamp():
            raise unauthorized
        user_id = int(payload["sub"])
        user = db.get(User, user_id)
        if user is None or bool(payload.get("is_guest")) != user.is_guest:
            raise unauthorized
        if user.is_guest and payload.get("guest_uuid") != user.guest_uuid:
            raise unauthorized
        return user
    except (JWTError, KeyError, TypeError, ValueError):
        raise unauthorized