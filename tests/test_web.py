from ledger.config import Settings
from ledger.db import Store
from ledger.providers.mock import MockProvider
from ledger.web import create_app


def test_dashboard_pages():
    settings = Settings(provider="mock", refresh_minutes=0, db_path=":memory:")
    app = create_app(settings, Store(":memory:"), MockProvider())
    c = app.test_client()
    assert "아직 계좌가 없습니다" in c.get("/").get_data(as_text=True)
    assert c.post("/sync").status_code == 302
    html = c.get("/").get_data(as_text=True)
    assert "총 자산" in html and "KB Star*t통장" in html
    assert c.get("/report").status_code == 200
    assert c.get("/compare").status_code == 200
    assert c.get("/api/balances").get_json()["total"] > 0
