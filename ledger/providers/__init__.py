"""데이터 공급자. 모두 fetch_accounts()와 fetch_transactions()를 제공한다."""
from __future__ import annotations

from ..config import Settings


def make_provider(settings: Settings, store=None):
    if settings.provider == "codef":
        from .codef import CodefProvider
        return CodefProvider(settings, store)
    if settings.provider == "mock":
        from .mock import MockProvider
        return MockProvider()
    raise ValueError(f"알 수 없는 LEDGER_PROVIDER: {settings.provider}")
