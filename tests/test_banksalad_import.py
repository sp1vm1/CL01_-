from datetime import datetime, time

from openpyxl import Workbook

from ledger.db import Store
from ledger.importers.banksalad import read_accounts, read_transactions
from ledger.sync import import_banksalad


def make_file(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "뱅샐현황"
    ws.append([None])
    ws.append([None, "3.재무현황"])
    ws.append([None, "자산", None, None, "부채"])
    ws.append([None, "항목", "상품명", None, "금액", "항목", "상품명", None, "금액"])
    ws.append([None, "자유입출금 자산", "KB Star*t통장-저축예금", None, 45704])
    ws.append([None, None, "입출금통장", None, 24993566])
    ws.append([None, "저축성 자산", "KB청년도약계좌", None, 7000000])
    ws.append([None, "투자성 자산", "종합매매", None, 8256248.632])
    ws.append([None, "총자산", 0])
    ws.append([None, "4.보험현황"])
    t = wb.create_sheet("가계부 내역")
    t.append(["날짜", "시간", "타입", "대분류", "소분류", "내용", "금액", "화폐", "결제수단", "메모"])
    t.append([datetime(2026, 9, 7), time(19, 37, 27), "지출", "카페/간식", "커피/음료", "흥국09026", -80226, "KRW", "KB Star*t통장-저축예금", None])
    t.append([datetime(2026, 9, 4), time(10, 37, 49), "수입", "용돈", "미분류", "대주회계급여", 3916770, "KRW", "KB Star*t통장-저축예금", None])
    t.append([datetime(2026, 9, 4), time(13, 27, 55), "이체", "내계좌이체", "미분류", "윤석영", -2000000, "KRW", "KB Star*t통장-저축예금", None])
    t.append([datetime(2026, 9, 11), time(18, 13, 37), "지출", "온라인쇼핑", "인터넷쇼핑", "쿠팡(쿠페이)", -373000, "KRW", "KB국민 노리2 체크카드", None])
    p = tmp_path / "bs.xlsx"
    wb.save(p)
    return p


def test_read_accounts_and_transactions(tmp_path):
    p = make_file(tmp_path)
    accts = read_accounts(p)
    assert [(a.name, a.kind, a.balance) for a in accts] == [
        ("KB Star*t통장-저축예금", "deposit", 45704), ("입출금통장", "deposit", 24993566),
        ("KB청년도약계좌", "savings", 7000000), ("종합매매", "investment", 8256249)]
    txs = read_transactions(p)
    assert len(txs) == 4 and txs[2].category == "이체"


def test_import_fixes_categories_and_dedupes(tmp_path):
    p = make_file(tmp_path)
    store = Store(":memory:")
    r = import_banksalad(store, str(p))
    assert r["added"] == 4
    assert import_banksalad(store, str(p))["added"] == 0
    cats = {row["description"]: row["category"] for row in store.transactions("2026-09-01", "2026-09-30")}
    assert cats["흥국09026"] == "보험" and cats["대주회계급여"] == "급여" and cats["쿠팡(쿠페이)"] == "온라인쇼핑"
