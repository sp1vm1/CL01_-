"""공급자에서 계좌·거래를 받아 DB 에 넣는다. 거래에는 분류 규칙을 적용한다."""
from __future__ import annotations

from .categorize import categorize, load_rules
from .db import Store, now_iso


def sync(store: Store, provider, days: int = 31) -> dict:
    started = now_iso()
    try:
        accounts = provider.fetch_accounts()
        store.upsert_accounts(accounts)
        txs = provider.fetch_transactions(accounts, days=days)
        rules = load_rules()
        for t in txs:
            if not t.category:
                t.category, t.subcategory = categorize(t.description, t.amount, rules)
        added = store.upsert_transactions(txs)
        msg = f"계좌 {len(accounts)}개, 거래 {len(txs)}건 조회, 신규 {added}건"
        store.log_sync(provider.name, True, msg, started)
        return {"ok": True, "accounts": len(accounts), "transactions": len(txs), "added": added, "message": msg}
    except Exception as e:  # noqa: BLE001 - 실패도 로그에 남긴다
        store.log_sync(getattr(provider, "name", "?"), False, str(e), started)
        return {"ok": False, "message": str(e)}


def import_banksalad(store: Store, path: str) -> dict:
    from .importers.banksalad import read_accounts, read_transactions

    rules = load_rules()
    txs = read_transactions(path)
    for t in txs:
        # 뱅크샐러드 분류를 존중하되, 규칙에 '보험'처럼 명시적 교정이 있으면 덮어쓴다
        cat, sub = categorize(t.description, t.amount, rules)
        if cat in ("보험", "급여") or t.category in ("", "미분류"):
            t.category, t.subcategory = cat, sub
    accounts = read_accounts(path)
    store.upsert_accounts(accounts)
    added = store.upsert_transactions(txs)
    store.log_sync("banksalad", True, f"{path}: 계좌 {len(accounts)}개, 거래 {len(txs)}건, 신규 {added}건", now_iso())
    return {"accounts": len(accounts), "transactions": len(txs), "added": added}
