from pathlib import Path
import os

from sqlalchemy import JSON, DateTime, Integer, String, create_engine, func
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


DB_PATH = Path(__file__).resolve().parent.parent / "advisor.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    wallet_address: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True, default=None)
    nonce: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(16), default="student")
    badges: Mapped[list[str]] = mapped_column(JSON, default=list)
    balance_fa: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BroadcastLog(Base):
    __tablename__ = "broadcast_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    audience: Mapped[str] = mapped_column(String(20), default="all")
    recipient_telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    message: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="failed")
    error: Mapped[str] = mapped_column(String(400), default="")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TransferLog(Base):
    __tablename__ = "transfer_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    from_telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    to_telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    from_wallet: Mapped[str] = mapped_column(String(42))
    to_wallet: Mapped[str] = mapped_column(String(42))
    amount: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


def apply_sqlite_migrations() -> None:
    with engine.connect() as conn:
        if not DATABASE_URL.startswith("sqlite"):
            return
        columns = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        column_names = {col[1] for col in columns}
        if "role" not in column_names:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(16) DEFAULT 'student'"))
            conn.commit()

