"""공급자와 무관한 공통 데이터 모델."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class Account:
    id: str                 # 공급자 내에서 고유한 키 (예: codef:0004:1234567890)
    provider: str           # codef | mock | banksalad
    bank: str               # 은행/기관 이름
    name: str               # 상품명 (예: KB Star*t통장)
    number: str             # 계좌번호 (마스킹 가능)
    kind: str               # deposit | savings | investment | pension | loan | pay | other
    balance: int
    currency: str = "KRW"
    org_code: str = ""


@dataclass
class Transaction:
    account_id: str
    date: str               # YYYY-MM-DD
    time: str               # HH:MM:SS ("" 가능)
    description: str
    amount: int             # 입금 +, 출금 -
    balance_after: int | None = None
    category: str = ""
    subcategory: str = ""
    memo: str = ""
    source: str = ""
    id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.id:
            raw = f"{self.account_id}|{self.date}|{self.time}|{self.amount}|{self.description}"
            self.id = hashlib.sha1(raw.encode("utf-8")).hexdigest()
