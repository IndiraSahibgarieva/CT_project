import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal, User


security = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_telegram_init_data(init_data: str, max_age_seconds: int = 3600) -> dict:
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN is not configured")
    pairs = parse_qsl(init_data, keep_blank_values=True)
    data = {k: v for k, v in pairs}
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing Telegram hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items(), key=lambda item: item[0]))
    secret_key = hmac.new(b"WebAppData", settings.telegram_bot_token.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received_hash, computed_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram initData signature")

    auth_date = int(data.get("auth_date", "0"))
    if auth_date <= 0 or (int(time.time()) - auth_date) > max_age_seconds:
        raise HTTPException(status_code=401, detail="Telegram auth data expired")

    user_raw = data.get("user")
    if not user_raw:
        raise HTTPException(status_code=401, detail="Missing Telegram user payload")
    return json.loads(user_raw)


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_exp_minutes)
    to_encode = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = decode_token(credentials.credentials)
    telegram_id_raw = payload.get("sub")
    if not telegram_id_raw:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    user = db.query(User).filter(User.telegram_id == int(telegram_id_raw)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user

