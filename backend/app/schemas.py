from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class NonceRequest(BaseModel):
    telegram_id: int = Field(..., gt=0)
    wallet_address: str = Field(..., min_length=42, max_length=42)


class NonceResponse(BaseModel):
    nonce: str
    challenge_message: str


class VerifyRequest(BaseModel):
    telegram_id: int = Field(..., gt=0)
    wallet_address: str = Field(..., min_length=42, max_length=42)
    signature: str = Field(..., min_length=40)


class AuthResponse(BaseModel):
    success: bool
    message: str
    access_token: str | None = None
    token_type: str = "bearer"
    role: str | None = None


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(..., min_length=20)


class DashboardResponse(BaseModel):
    telegram_id: int
    wallet_address: str
    balance_fa: float
    badges: list[str]
    notifications: list[str]


class BroadcastRequest(BaseModel):
    audience: str = Field(default="all")
    message: str = Field(..., min_length=5, max_length=500)


class BroadcastResponse(BaseModel):
    delivered: int
    failed: int = 0
    queued: bool = True


class BroadcastLogItem(BaseModel):
    recipient_telegram_id: int
    status: str
    error: str | None = None
    created_at: str | None = None


class MeResponse(BaseModel):
    telegram_id: int
    role: str
    wallet_address: str | None = None


class TransferRequest(BaseModel):
    to_wallet: str = Field(..., min_length=42, max_length=42)
    amount: float = Field(..., gt=0)


class TransferResponse(BaseModel):
    success: bool
    message: str
    new_balance: float | None = None

