"""SQLite 저장소. 재실행해도 중복이 쌓이지 않도록 모든 삽입은 upsert."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from .models import Account, Transaction

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    bank TEXT NOT NULL,
    name TEXT NOT NULL,
    number TEXT NOT NULL,
    kind TEXT NOT NULL,
    balance INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'KRW',
    org_code TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER,
    category TEXT NOT NULL DEFAULT '',
    subcategory TEXT NOT NULL DEFAULT '',
    memo TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id, date);
CREATE TABLE IF NOT EXISTS balance_snapshots (
    account_id TEXT NOT NULL,
    taken_at TEXT NOT NULL,
    balance INTEGER NOT NULL,
    PRIMARY KEY (account_id, taken_at)
);
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    ok INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # ----- accounts -----
    def upsert_accounts(self, accounts: Iterable[Account], snapshot: bool = True) -> int:
        ts = now_iso()
        n = 0
        for a in accounts:
            self.conn.execute(
                """INSERT INTO accounts(id,provider,bank,name,number,kind,balance,currency,org_code,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET provider=excluded.provider, bank=excluded.bank,
                     name=excluded.name, number=excluded.number, kind=excluded.kind,
                     balance=excluded.balance, currency=excluded.currency, org_code=excluded.org_code,
                     updated_at=excluded.updated_at""",
                (a.id, a.provider, a.bank, a.name, a.number, a.kind, a.balance, a.currency, a.org_code, ts),
            )
            if snapshot:
                self.conn.execute(
                    "INSERT OR REPLACE INTO balance_snapshots(account_id,taken_at,balance) VALUES(?,?,?)",
                    (a.id, ts, a.balance),
                )
            n += 1
        self.conn.commit()
        return n

    def accounts(self, provider: str | None = None) -> list[sqlite3.Row]:
        if provider:
            return self.conn.execute("SELECT * FROM accounts WHERE provider=? ORDER BY kind, bank, name", (provider,)).fetchall()
        return self.conn.execute("SELECT * FROM accounts ORDER BY kind, bank, name").fetchall()

    # ----- transactions -----
    def upsert_transactions(self, txs: Iterable[Transaction]) -> int:
        rows = [
            (t.id, t.account_id, t.date, t.time, t.description, t.amount, t.balance_after,
             t.category, t.subcategory, t.memo, t.source)
            for t in txs
        ]
        before = self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        self.conn.executemany(
            """INSERT INTO transactions(id,account_id,date,time,description,amount,balance_after,
                                        category,subcategory,memo,source)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET balance_after=COALESCE(excluded.balance_after, balance_after),
                 category=CASE WHEN excluded.category<>'' THEN excluded.category ELSE category END,
                 subcategory=CASE WHEN excluded.subcategory<>'' THEN excluded.subcategory ELSE subcategory END""",
            rows,
        )
        self.conn.commit()
        after = self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        return after - before

    def transactions(self, start: str, end: str, account_id: str | None = None,
                     provider: str | None = None) -> list[sqlite3.Row]:
        sql = "SELECT t.* FROM transactions t WHERE t.date BETWEEN ? AND ?"
        args: list = [start, end]
        if account_id:
            sql += " AND t.account_id=?"
            args.append(account_id)
        if provider:
            sql += " AND t.source=?"
            args.append(provider)
        sql += " ORDER BY t.date DESC, t.time DESC"
        return self.conn.execute(sql, args).fetchall()

    def set_category(self, tx_id: str, category: str, subcategory: str = "") -> None:
        self.conn.execute("UPDATE transactions SET category=?, subcategory=? WHERE id=?", (category, subcategory, tx_id))
        self.conn.commit()

    # ----- sync log / kv -----
    def log_sync(self, provider: str, ok: bool, message: str, started_at: str) -> None:
        self.conn.execute(
            "INSERT INTO sync_log(provider,started_at,finished_at,ok,message) VALUES(?,?,?,?,?)",
            (provider, started_at, now_iso(), int(ok), message),
        )
        self.conn.commit()

    def last_sync(self) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1").fetchone()

    def kv_get(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def kv_set(self, key: str, value: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO kv(key,value) VALUES(?,?)", (key, value))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
