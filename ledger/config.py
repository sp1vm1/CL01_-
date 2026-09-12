"""환경 변수 기반 설정. .env 파일이 있으면 먼저 읽는다."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def load_dotenv(path: str | os.PathLike = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.split("  #")[0].strip()  # 값 뒤 주석 제거
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class BankLogin:
    organization: str
    user_id: str
    password: str


@dataclass
class Settings:
    provider: str = "mock"
    codef_env: str = "sandbox"
    codef_client_id: str = ""
    codef_client_secret: str = ""
    codef_public_key: str = ""
    bank_logins: list[BankLogin] = field(default_factory=list)
    db_path: str = "data/ledger.db"
    refresh_minutes: int = 10

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        logins: list[BankLogin] = []
        raw = os.environ.get("CODEF_BANK_LOGINS", "").strip()
        for item in filter(None, (s.strip() for s in raw.split(";"))):
            parts = item.split(":", 2)
            if len(parts) != 3:
                raise ValueError(f"CODEF_BANK_LOGINS 형식 오류: {item!r} (기관코드:아이디:비밀번호)")
            logins.append(BankLogin(*parts))
        return cls(
            provider=os.environ.get("LEDGER_PROVIDER", "mock").strip(),
            codef_env=os.environ.get("CODEF_ENV", "sandbox").strip(),
            codef_client_id=os.environ.get("CODEF_CLIENT_ID", "").strip(),
            codef_client_secret=os.environ.get("CODEF_CLIENT_SECRET", "").strip(),
            codef_public_key=os.environ.get("CODEF_PUBLIC_KEY", "").strip(),
            bank_logins=logins,
            db_path=os.environ.get("LEDGER_DB", "data/ledger.db").strip(),
            refresh_minutes=int(os.environ.get("LEDGER_REFRESH_MINUTES", "10")),
        )
