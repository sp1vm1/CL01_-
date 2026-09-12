"""명령줄 인터페이스.

  python -m ledger.cli sync                      공급자에서 계좌·거래 가져오기
  python -m ledger.cli import-banksalad 파일.xlsx 뱅크샐러드 내보내기 가져오기
  python -m ledger.cli balances                  계좌 잔액 출력
  python -m ledger.cli report 2026-09            월 수입/지출
  python -m ledger.cli compare 2026-08 2026-09   두 달 지출 비교
  python -m ledger.cli web                       대시보드 실행 (http://127.0.0.1:5000)
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from .config import Settings
from .db import Store
from .report import balances, compare, monthly


def fmt(n: int) -> str:
    return f"{n:,}원"


def cmd_sync(args, settings, store):
    from .providers import make_provider
    from .sync import sync

    r = sync(store, make_provider(settings, store), days=args.days)
    print(("완료: " if r["ok"] else "실패: ") + r["message"])
    return 0 if r["ok"] else 1


def cmd_import(args, settings, store):
    from .sync import import_banksalad

    r = import_banksalad(store, args.file)
    print(f"가져오기 완료: 계좌 {r['accounts']}개, 거래 {r['transactions']}건, 신규 {r['added']}건")
    return 0


def cmd_balances(args, settings, store):
    b = balances(store, args.provider)
    for _, label, accts, subtotal in b["groups"]:
        print(f"\n[{label}] {fmt(subtotal)}")
        for a in accts:
            print(f"  {a['name']:<34} {a['bank']:<10} {fmt(a['balance']):>16}   ({a['updated_at'][:16]})")
    print(f"\n총 자산 {fmt(b['total'])}")
    last = store.last_sync()
    if last:
        print(f"마지막 동기화: {last['finished_at']} {'성공' if last['ok'] else '실패'} - {last['message']}")
    return 0


def cmd_report(args, settings, store):
    r = monthly(store, args.month, provider=args.provider)
    print(f"{r['month']}  수입 {fmt(r['income_total'])}  지출 {fmt(r['expense_total'])}  순수입 {fmt(r['income_total'] - r['expense_total'])}")
    if r["duplicates_removed"]:
        print(f"(페이 중복 {r['duplicates_removed']}건 제외)")
    print("\n지출 카테고리")
    for c, v in r["expense"].items():
        pct = 100 * v / r["expense_total"] if r["expense_total"] else 0
        print(f"  {c:<10} {fmt(v):>14}  {pct:4.0f}%")
    print("\n수입 항목")
    for c, v in r["income"].items():
        print(f"  {c:<10} {fmt(v):>14}")
    print("\n큰 지출")
    for t in r["top_expenses"]:
        print(f"  {t['date']} {t['description'][:24]:<24} {t['category']:<8} {fmt(t['amount']):>14}")
    return 0


def cmd_compare(args, settings, store):
    print(f"{'카테고리':<10} {args.a:>12} {args.b:>12} {'증감':>12}")
    for c, x, y, d in compare(store, args.a, args.b, provider=args.provider):
        print(f"{c:<10} {x:>12,} {y:>12,} {d:>+12,}")
    return 0


def cmd_web(args, settings, store):
    from .web import create_app

    app = create_app(settings, store)
    print(f"http://{args.host}:{args.port}  (Ctrl+C 로 종료)")
    app.run(host=args.host, port=args.port, debug=False)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ledger", description="통합 계좌 조회 + 가계부")
    p.add_argument("--db", help="SQLite 경로 (기본: LEDGER_DB 또는 data/ledger.db)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync"); s.add_argument("--days", type=int, default=31); s.set_defaults(fn=cmd_sync)
    s = sub.add_parser("import-banksalad"); s.add_argument("file"); s.set_defaults(fn=cmd_import)
    s = sub.add_parser("balances"); s.add_argument("--provider"); s.set_defaults(fn=cmd_balances)
    s = sub.add_parser("report"); s.add_argument("month", nargs="?", default=date.today().strftime("%Y-%m")); s.add_argument("--provider"); s.set_defaults(fn=cmd_report)
    s = sub.add_parser("compare"); s.add_argument("a"); s.add_argument("b"); s.add_argument("--provider"); s.set_defaults(fn=cmd_compare)
    s = sub.add_parser("web"); s.add_argument("--host", default="127.0.0.1"); s.add_argument("--port", type=int, default=5000); s.set_defaults(fn=cmd_web)
    args = p.parse_args(argv)
    settings = Settings.from_env()
    if args.db:
        settings.db_path = args.db
    store = Store(settings.db_path)
    try:
        return args.fn(args, settings, store)
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
