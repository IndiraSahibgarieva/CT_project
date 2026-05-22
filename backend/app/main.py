from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, get_db, require_admin, verify_telegram_init_data
from .database import Base, BroadcastLog, TransferLog, User, apply_sqlite_migrations, engine
from .schemas import (
    AuthResponse,
    BroadcastLogItem,
    BroadcastRequest,
    BroadcastResponse,
    DashboardResponse,
    HealthResponse,
    MeResponse,
    NonceRequest,
    NonceResponse,
    TelegramAuthRequest,
    TransferRequest,
    TransferResponse,
    VerifyRequest,
)
from .services import (
    create_nonce,
    fake_chain_snapshot,
    resolve_role,
    send_telegram_message,
    upsert_user,
    verify_wallet_signature,
)
from .web3_client import get_fa_balance


Base.metadata.create_all(bind=engine)
apply_sqlite_migrations()

app = FastAPI(title="Telegram Web3 Advisor API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse()


@app.post("/api/auth/telegram", response_model=AuthResponse)
def telegram_auth(payload: TelegramAuthRequest, db: Session = Depends(get_db)):
    tg_user = verify_telegram_init_data(payload.init_data)
    telegram_id = int(tg_user["id"])
    role = resolve_role(telegram_id)
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, wallet_address=None, role=role)
        db.add(user)
    user.role = role
    db.commit()
    access_token = create_access_token(subject=str(telegram_id), role=role)
    return AuthResponse(
        success=True,
        message="Telegram authentication successful",
        access_token=access_token,
        token_type="bearer",
        role=role,
    )


@app.get("/api/auth/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        telegram_id=current_user.telegram_id,
        role=current_user.role,
        wallet_address=current_user.wallet_address or None,
    )


@app.post("/api/auth/nonce", response_model=NonceResponse)
def generate_nonce(payload: NonceRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.telegram_id != current_user.telegram_id:
        raise HTTPException(status_code=403, detail="Token does not match telegram_id")
    wallet_address = payload.wallet_address.lower()
    nonce, challenge_message = create_nonce(payload.telegram_id, wallet_address)
    upsert_user(db, payload.telegram_id, wallet_address, nonce)
    db.commit()
    return NonceResponse(nonce=nonce, challenge_message=challenge_message)


@app.post("/api/auth/verify", response_model=AuthResponse)
def verify_signature(payload: VerifyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.telegram_id != current_user.telegram_id:
        raise HTTPException(status_code=403, detail="Token does not match telegram_id")
    user = db.query(User).filter(User.telegram_id == payload.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User session not found")

    message = (
        "Telegram Web3 Advisor sign-in\n"
        f"Telegram ID: {payload.telegram_id}\n"
        f"Wallet: {payload.wallet_address.lower()}\n"
        f"Nonce: {user.nonce}"
    )
    try:
        verified = verify_wallet_signature(payload.wallet_address, message, payload.signature)
    except Exception as exc:  # nosec - signature parser throws many subclasses
        raise HTTPException(status_code=400, detail=f"Invalid signature payload: {exc}") from exc

    if not verified:
        raise HTTPException(status_code=401, detail="Signature verification failed")

    try:
        balance = get_fa_balance(payload.wallet_address.lower())
    except Exception:
        balance, _ = fake_chain_snapshot(payload.wallet_address.lower())
    _, badges = fake_chain_snapshot(payload.wallet_address.lower())
    user.balance_fa = balance
    user.badges = badges
    db.commit()
    access_token = create_access_token(subject=str(user.telegram_id), role=user.role)
    return AuthResponse(
        success=True,
        message="Wallet linked successfully",
        access_token=access_token,
        token_type="bearer",
        role=user.role,
    )


@app.get("/api/dashboard/me", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.telegram_id == current_user.telegram_id).first()
    if not user or not user.wallet_address:
        raise HTTPException(status_code=404, detail="Linked wallet not found")
    try:
        user.balance_fa = get_fa_balance(user.wallet_address.lower())
        db.commit()
    except Exception:
        pass
    notifications = [
        "Начислено 15 FA-токенов за участие в голосовании",
        "Открыто новое голосование по треку Web3",
        "Доступен бейдж за недельную активность",
    ]
    return DashboardResponse(
        telegram_id=user.telegram_id,
        wallet_address=user.wallet_address,
        balance_fa=user.balance_fa,
        badges=user.badges or [],
        notifications=notifications,
    )


@app.post("/api/admin/broadcast", response_model=BroadcastResponse)
def broadcast(payload: BroadcastRequest, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    audience = payload.audience.lower().strip()
    query = db.query(User)
    if audience in {"admin", "admins"}:
        query = query.filter(User.role == "admin")
    elif audience in {"student", "students"}:
        query = query.filter(User.role == "student")

    recipients = query.all()
    delivered = 0
    failed = 0
    for user in recipients:
        ok, error = send_telegram_message(user.telegram_id, payload.message)
        log = BroadcastLog(
            audience=audience,
            recipient_telegram_id=user.telegram_id,
            message=payload.message,
            status="delivered" if ok else "failed",
            error=error[:400] if error else "",
        )
        db.add(log)
        if ok:
            delivered += 1
        else:
            failed += 1
    db.commit()
    return BroadcastResponse(delivered=delivered, failed=failed, queued=False)


@app.get("/api/admin/broadcast/logs", response_model=list[BroadcastLogItem])
def broadcast_logs(limit: int = 100, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    safe_limit = max(1, min(limit, 500))
    logs = db.query(BroadcastLog).order_by(BroadcastLog.id.desc()).limit(safe_limit).all()
    return [
        BroadcastLogItem(
            recipient_telegram_id=item.recipient_telegram_id,
            status=item.status,
            error=item.error or None,
            created_at=str(item.created_at) if item.created_at else None,
        )
        for item in logs
    ]


@app.post("/api/transfer", response_model=TransferResponse)
def transfer_tokens(
    payload: TransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.wallet_address:
        raise HTTPException(status_code=400, detail="Привяжите кошелёк перед переводом")

    to_wallet = payload.to_wallet.lower()
    if to_wallet == current_user.wallet_address.lower():
        raise HTTPException(status_code=400, detail="Нельзя переводить токены самому себе")

    sender = db.query(User).filter(User.telegram_id == current_user.telegram_id).first()
    if sender.balance_fa < payload.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Недостаточно токенов. Баланс: {sender.balance_fa} FA",
        )

    recipient = db.query(User).filter(User.wallet_address == to_wallet).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Получатель с таким адресом не зарегистрирован")

    amount = round(payload.amount, 6)
    sender.balance_fa = round(sender.balance_fa - amount, 6)
    recipient.balance_fa = round(recipient.balance_fa + amount, 6)

    log = TransferLog(
        from_telegram_id=sender.telegram_id,
        to_telegram_id=recipient.telegram_id,
        from_wallet=sender.wallet_address,
        to_wallet=to_wallet,
        amount=amount,
    )
    db.add(log)
    db.commit()

    short_to = f"{payload.to_wallet[:6]}...{payload.to_wallet[-4:]}"
    return TransferResponse(
        success=True,
        message=f"Успешно переведено {amount} FA → {short_to}",
        new_balance=sender.balance_fa,
    )


# Local dev: backend/app/main.py -> ../../.. -> project root
# Docker:    /app/app/main.py   -> ../..   -> /app
_base = Path(__file__).resolve().parent
frontend_dir = None
for _up in (_base.parent.parent.parent, _base.parent.parent, _base.parent):
    _candidate = _up / "frontend"
    if _candidate.is_dir():
        frontend_dir = _candidate
        break

if frontend_dir is not None:
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

