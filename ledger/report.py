"""잔액 요약과 월별 수입/지출 리포트."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from .categorize import dedupe_key, is_transfer
from .db import Store

KIND_LABEL = {"deposit": "입출금", "savings": "저축", "pay": "페이머니", "investment": "투자",
              "pension": "연금", "loan": "대출", "other": "기타"}
KIND_ORDER = ["deposit", "savings", "pay", "investment", "pension", "other", "loan"]


def balances(store: Store, provider: str | None = None) -> dict:
    groups: dict[str, list] = defaultdict(list)
    for a in store.accounts(provider):
        groups[a["kind"]].append(dict(a))
    ordered = [(k, KIND_LABEL.get(k, k), groups[k], sum(x["balance"] for x in groups[k]))
               for k in KIND_ORDER if groups.get(k)]
    total = sum(g[3] for g in ordered)
    return {"groups": ordered, "total": total}


def month_range(ym: str) -> tuple[str, str]:
    y, m = int(ym[:4]), int(ym[5:7])
    last = date(y + (m == 12), (m % 12) + 1, 1).toordinal() - 1
    return f"{ym}-01", date.fromordinal(last).isoformat()


INCOME_CATEGORIES = {"급여", "금융수입", "기타수입", "용돈", "수입", "월수입"}


def monthly(store: Store, ym: str, drop_duplicates: bool = True, provider: str | None = None) -> dict:
    start, end = month_range(ym)
    rows = [dict(r) for r in store.transactions(start, end, provider=provider)]
    if drop_duplicates:
        seen: set = set()
        uniq = []
        for r in rows:
            k = dedupe_key(r)
            if k in seen and r["amount"] < 0:
                continue
            seen.add(k)
            uniq.append(r)
        dup_count = len(rows) - len(uniq)
        rows = uniq
    else:
        dup_count = 0
    income = defaultdict(int)
    expense = defaultdict(int)
    for r in rows:
        if is_transfer(r["category"]):
            continue
        cat = r["category"]
        if r["amount"] > 0 and (not cat or cat in INCOME_CATEGORIES):
            income[cat or "기타수입"] += r["amount"]
        else:  # 지출 카테고리의 양수는 환불이므로 지출에서 차감
            expense[cat or "미분류"] += -r["amount"]
    top = sorted((r for r in rows if r["amount"] < 0 and not is_transfer(r["category"])), key=lambda r: r["amount"])[:15]
    return {
        "month": ym, "start": start, "end": end,
        "income": dict(sorted(income.items(), key=lambda kv: -kv[1])),
        "expense": dict(sorted(expense.items(), key=lambda kv: -kv[1])),
        "income_total": sum(income.values()), "expense_total": sum(expense.values()),
        "top_expenses": top, "duplicates_removed": dup_count, "count": len(rows),
    }


def compare(store: Store, ym_a: str, ym_b: str, provider: str | None = None) -> list[tuple[str, int, int, int]]:
    a, b = monthly(store, ym_a, provider=provider), monthly(store, ym_b, provider=provider)
    cats = set(a["expense"]) | set(b["expense"])
    out = [(c, a["expense"].get(c, 0), b["expense"].get(c, 0), b["expense"].get(c, 0) - a["expense"].get(c, 0)) for c in cats]
    return sorted(out, key=lambda x: x[3])
