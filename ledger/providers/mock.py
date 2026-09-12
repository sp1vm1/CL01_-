"""자격증명 없이 프로그램을 돌려볼 수 있는 모의 공급자. 실제 사용자 데이터가 아니다."""
from __future__ import annotations

import random
from datetime import date, timedelta

from ..models import Account, Transaction

SAMPLE_ACCOUNTS = [
    ("0004", "KB국민은행", "KB Star*t통장", "123456-**-****01", "deposit", 1_250_000),
    ("0092", "토스뱅크", "토스뱅크 통장", "1000-****-****2", "deposit", 340_000),
    ("0090", "카카오뱅크", "입출금통장", "3333-**-*****3", "deposit", 8_900_000),
    ("0011", "NH농협은행", "자유저축예탁금", "302-****-****-41", "deposit", 129_000),
    ("0004", "KB국민은행", "KB청년도약계좌", "123456-**-****09", "savings", 7_000_000),
    ("0011", "NH농협은행", "주택청약종합저축", "302-****-****-77", "savings", 5_550_000),
]
MERCHANTS = [("급여", 3_900_000), ("쿠팡", -38_000), ("스타벅스", -6_100), ("GS25", -4_200),
             ("배달의민족", -21_000), ("ABL생명", -302_205), ("KT통신요금", -27_500),
             ("한국철도공사", -35_900), ("다이소", -10_000), ("카카오페이", -20_000)]


class MockProvider:
    name = "mock"

    def fetch_accounts(self) -> list[Account]:
        return [
            Account(id=f"mock:{org}:{num}", provider="mock", bank=bank, name=name, number=num,
                    kind=kind, balance=bal, org_code=org)
            for org, bank, name, num, kind, bal in SAMPLE_ACCOUNTS
        ]

    def fetch_transactions(self, accounts: list[Account], days: int = 31) -> list[Transaction]:
        rng = random.Random(42)  # 매번 같은 데이터가 나오도록 고정
        txs: list[Transaction] = []
        today = date.today()
        deposits = [a for a in accounts if a.kind == "deposit"]
        for i in range(days):
            d = today - timedelta(days=i)
            for _ in range(rng.randint(1, 3)):
                desc, amt = rng.choice(MERCHANTS)
                if desc == "급여" and d.day != 5:
                    continue
                acct = deposits[0] if desc in ("급여", "ABL생명", "KT통신요금") else rng.choice(deposits)
                txs.append(Transaction(
                    account_id=acct.id, date=d.isoformat(), time=f"{rng.randint(8, 22):02d}:{rng.randint(0, 59):02d}:00",
                    description=desc, amount=amt + (0 if desc in ("급여", "ABL생명", "KT통신요금") else rng.randint(-2000, 2000)),
                    source="mock",
                ))
        return txs
