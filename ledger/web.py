"""로컬 웹 대시보드. 잔액을 주기적으로 갱신하고 버튼으로 즉시 새로고침한다."""
from __future__ import annotations

import threading
import time
from datetime import date

from flask import Flask, redirect, render_template_string, request, url_for

from .config import Settings
from .db import Store
from .providers import make_provider
from .report import balances, compare, monthly
from .sync import sync

PAGE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>통합 계좌 조회</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--fg:#1a1d21;--muted:#6b7280;--line:#e5e7eb;--accent:#2563eb;--neg:#dc2626;--pos:#16a34a}
@media(prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--fg:#e5e7eb;--muted:#9ca3af;--line:#262a33;--accent:#60a5fa;--neg:#f87171;--pos:#4ade80}}
*{box-sizing:border-box}body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif}
.wrap{max-width:900px;margin:0 auto}h1{font-size:20px;margin:0 0 4px}.muted{color:var(--muted);font-size:13px}
.total{font-size:32px;font-weight:700;margin:8px 0 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:12px}
.row{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-top:1px solid var(--line)}.row:first-of-type{border-top:0}
.row .n{color:var(--muted);font-size:13px}.amt{font-variant-numeric:tabular-nums;white-space:nowrap}
.neg{color:var(--neg)}.pos{color:var(--pos)}
.head{display:flex;justify-content:space-between;align-items:baseline}
button,.btn{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:8px 14px;font-size:14px;cursor:pointer;text-decoration:none}
nav a{margin-right:12px}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:6px 4px;border-top:1px solid var(--line);text-align:left}
td.amt,th.amt{text-align:right}.err{color:var(--neg)}
</style></head><body><div class="wrap">
<div class="head"><h1>통합 계좌 조회</h1>
<form method="post" action="{{ url_for('do_sync') }}"><button>지금 새로고침</button></form></div>
<div class="muted">공급자: {{ provider }} · 마지막 동기화: {% if last %}{{ last['finished_at'] }} ({{ '성공' if last['ok'] else '실패' }}) {{ last['message'] }}{% else %}없음{% endif %}
· 자동 갱신 {{ refresh }}분</div>
<nav class="muted" style="margin:8px 0 12px"><a href="{{ url_for('index') }}">잔액</a><a href="{{ url_for('report', month=this_month) }}">이번 달</a><a href="{{ url_for('report', month=prev_month) }}">지난 달</a><a href="{{ url_for('cmp', a=prev_month, b=this_month) }}">비교</a></nav>
{% block body %}{% endblock %}
</div></body></html>"""

INDEX = """{% extends "base" %}{% block body %}
<div class="muted">총 자산</div><div class="total">{{ "{:,}".format(b.total) }}원</div>
{% for kind, label, accts, subtotal in b.groups %}
<div class="card"><div class="head"><strong>{{ label }}</strong><span class="amt">{{ "{:,}".format(subtotal) }}원</span></div>
{% for a in accts %}<div class="row"><div>{{ a.name }}<div class="n">{{ a.bank }} {{ a.number }} · {{ a.updated_at[:16] }}</div></div>
<div class="amt {{ 'neg' if a.balance < 0 else '' }}">{{ "{:,}".format(a.balance) }}원</div></div>{% endfor %}
</div>{% endfor %}
{% if not b.groups %}<div class="card">아직 계좌가 없습니다. "지금 새로고침"을 누르거나 <code>python -m ledger.cli sync</code> 를 실행하세요.</div>{% endif %}
{% endblock %}"""

REPORT = """{% extends "base" %}{% block body %}
<div class="card"><div class="head"><strong>{{ r.month }} 수입 / 지출</strong><span class="muted">{{ r.count }}건{% if r.duplicates_removed %}, 페이 중복 {{ r.duplicates_removed }}건 제외{% endif %}</span></div>
<div class="row"><div>수입</div><div class="amt pos">{{ "{:,}".format(r.income_total) }}원</div></div>
<div class="row"><div>지출</div><div class="amt neg">{{ "{:,}".format(r.expense_total) }}원</div></div>
<div class="row"><div><strong>순수입</strong></div><div class="amt"><strong>{{ "{:,}".format(r.income_total - r.expense_total) }}원</strong></div></div></div>
<div class="card"><strong>지출 카테고리</strong>
{% for c, v in r.expense.items() %}<div class="row"><div>{{ c }}</div><div class="amt">{{ "{:,}".format(v) }}원 <span class="muted">{{ (100*v/r.expense_total)|round(0)|int if r.expense_total else 0 }}%</span></div></div>{% endfor %}</div>
<div class="card"><strong>수입 항목</strong>
{% for c, v in r.income.items() %}<div class="row"><div>{{ c }}</div><div class="amt pos">{{ "{:,}".format(v) }}원</div></div>{% endfor %}</div>
<div class="card"><strong>큰 지출 15건</strong><table><tr><th>날짜</th><th>내용</th><th>분류</th><th class="amt">금액</th></tr>
{% for t in r.top_expenses %}<tr><td>{{ t.date[5:] }}</td><td>{{ t.description }}</td><td class="muted">{{ t.category }}</td><td class="amt">{{ "{:,}".format(t.amount) }}</td></tr>{% endfor %}</table></div>
{% endblock %}"""

COMPARE = """{% extends "base" %}{% block body %}
<div class="card"><strong>{{ a }} → {{ b }} 지출 비교</strong><table><tr><th>카테고리</th><th class="amt">{{ a }}</th><th class="amt">{{ b }}</th><th class="amt">증감</th></tr>
{% for c, x, y, d in rows %}<tr><td>{{ c }}</td><td class="amt">{{ "{:,}".format(x) }}</td><td class="amt">{{ "{:,}".format(y) }}</td><td class="amt {{ 'neg' if d > 0 else 'pos' }}">{{ "{:+,}".format(d) }}</td></tr>{% endfor %}</table></div>
{% endblock %}"""


def _prev_month(ym: str) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{y - (m == 1)}-{(m - 2) % 12 + 1:02d}"


def create_app(settings: Settings | None = None, store: Store | None = None, provider=None) -> Flask:
    settings = settings or Settings.from_env()
    store = store or Store(settings.db_path)
    app = Flask(__name__)
    app.jinja_loader = __import__("jinja2").DictLoader({"base": PAGE})
    lock = threading.Lock()

    def get_provider():
        nonlocal provider
        if provider is None:
            provider = make_provider(settings, store)
        return provider

    def run_sync():
        with lock:
            return sync(store, get_provider())

    def ctx(**kw):
        today = date.today().strftime("%Y-%m")
        return dict(provider=settings.provider, last=store.last_sync(), refresh=settings.refresh_minutes,
                    this_month=today, prev_month=_prev_month(today), **kw)

    @app.get("/")
    def index():
        return render_template_string(INDEX, b=balances(store), **ctx())

    @app.post("/sync")
    def do_sync():
        run_sync()
        return redirect(url_for("index"))

    @app.get("/report")
    def report():
        ym = request.args.get("month") or date.today().strftime("%Y-%m")
        return render_template_string(REPORT, r=monthly(store, ym, provider=request.args.get("provider")), **ctx())

    @app.get("/compare")
    def cmp():
        b = request.args.get("b") or date.today().strftime("%Y-%m")
        a = request.args.get("a") or _prev_month(b)
        return render_template_string(COMPARE, rows=compare(store, a, b, provider=request.args.get("provider")), a=a, b=b, **ctx())

    @app.get("/api/balances")
    def api_balances():
        b = balances(store)
        return {"total": b["total"], "groups": [{"kind": k, "label": l, "subtotal": s, "accounts": a} for k, l, a, s in b["groups"]]}

    def scheduler():
        while True:
            time.sleep(max(settings.refresh_minutes, 1) * 60)
            try:
                run_sync()
            except Exception:  # noqa: BLE001
                pass

    if settings.refresh_minutes > 0:
        threading.Thread(target=scheduler, daemon=True).start()
    app.config["run_sync"] = run_sync
    return app
