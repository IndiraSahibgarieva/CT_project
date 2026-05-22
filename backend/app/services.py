import hashlib
import secrets
from datetime import datetime

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy.orm import Session

from .config import settings
from .database import User


def create_nonce(telegram_id: int, wallet_address: str) -> tuple[str, str]:
    raw = f"{telegram_id}:{wallet_address}:{datetime.utcnow().isoformat()}:{secrets.token_hex(8)}"
    nonce = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    message = (
        "Telegram Web3 Advisor sign-in\n"
        f"Telegram ID: {telegram_id}\n"
        f"Wallet: {wallet_address}\n"
        f"Nonce: {nonce}"
    )
    return nonce, message


def verify_wallet_signature(wallet_address: str, message: str, signature: str) -> bool:
    encoded_message = encode_defunct(text=message)
    recovered_address = Account.recover_message(encoded_message, signature=signature)
    return recovered_address.lower() == wallet_address.lower()


def fake_chain_snapshot(wallet_address: str) -> tuple[float, list[str]]:
    seed = int(hashlib.sha256(wallet_address.encode("utf-8")).hexdigest(), 16)
    balance = round((seed % 1_500_000) / 10000, 2)
    badges_pool = ["NFT Pioneer", "Hackathon Hero", "Voter", "Community Voice", "Builder"]
    badges = [b for idx, b in enumerate(badges_pool) if (seed >> idx) & 1]
    return balance, badges or ["Newcomer"]


def upsert_user(session: Session, telegram_id: int, wallet_address: str, nonce: str) -> User:
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    if user is None:
        user = User(telegram_id=telegram_id, wallet_address=wallet_address)
        session.add(user)
    user.wallet_address = wallet_address
    user.nonce = nonce
    session.flush()
    return user


def resolve_role(telegram_id: int) -> str:
    admin_ids = {item.strip() for item in settings.admin_telegram_ids.split(",") if item.strip()}
    return "admin" if str(telegram_id) in admin_ids else "student"


def send_telegram_message(chat_id: int, text: str) -> tuple[bool, str]:
    if not settings.telegram_bot_token:
        return False, "TELEGRAM_BOT_TOKEN is not configured"
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
    except Exception as exc:
        return False, f"Network error: {exc}"
    if response.status_code != 200:
        return False, f"HTTP {response.status_code}: {response.text[:200]}"
    body = response.json()
    if not body.get("ok"):
        return False, str(body.get("description", "Unknown Telegram API error"))
    return True, ""

