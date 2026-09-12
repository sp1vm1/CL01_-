from datetime import date

from ledger.categorize import categorize, load_rules
from ledger.db import Store
from ledger.models import Account, Transaction
from ledger.report import balances, compare, monthly
from ledger.sync import sync
from ledger.providers.mock import MockProvider

RULES = load_rules(path=None)


def test_insurance_misclassifications_fixed():
    assert categorize("흥국09026", -80226, RULES)[0] == "보험"
    assert categorize("LINA2609026", -28540, RULES)[0] == "보험"
    assert categorize("ABL생명09023", -302205, RULES)[0] == "보험"


def test_salary_only_when_incoming():
    assert categorize("대주회계급여", 3916770, RULES)[0] == "급여"
    assert categorize("급여 반환", -1000, RULES)[0] != "급여"


def test_unknown_defaults():
    assert categorize("알수없는가게", -1000, RULES) == ("미분류", "")
    assert categorize("알수없는입금", 1000, RULES) == ("기타수입", "")


def test_sync_is_idempotent_and_report_excludes_transfers():
    store = Store(":memory:")
    r1 = sync(store, MockProvider(), days=40)
    r2 = sync(store, MockProvider(), days=40)
    assert r1["ok"] and r2["ok"]
    assert r1["added"] > 0 and r2["added"] == 0  # 재실행해도 중복 없음
    assert balances(store)["total"] == sum(a.balance for a in MockProvider().fetch_accounts())
    ym = date.today().strftime("%Y-%m")
    rep = monthly(store, ym)
    assert "이체" not in rep["expense"] and rep["expense_total"] >= 0


def test_pay_duplicate_is_dropped_once():
    store = Store(":memory:")
    store.upsert_accounts([Account(id="a1", provider="t", bank="b", name="n", number="", kind="deposit", balance=0),
                           Account(id="a2", provider="t", bank="b", name="n2", number="", kind="pay", balance=0)])
    store.upsert_transactions([
        Transaction(account_id="a1", date="2026-08-09", time="08:03:50", description="토스페이먼츠 주식회사", amount=-219450, category="금융"),
        Transaction(account_id="a2", date="2026-08-09", time="08:03:50", description="토스페이먼츠 주식회사", amount=-219450, category="온라인쇼핑"),
        Transaction(account_id="a1", date="2026-08-10", time="09:00:00", description="쿠팡", amount=-10000, category="온라인쇼핑"),
    ])
    rep = monthly(store, "2026-08")
    assert rep["duplicates_removed"] == 1 and rep["expense_total"] == 229450
    rows = compare(store, "2026-07", "2026-08")
    assert sum(r[3] for r in rows) == 229450
