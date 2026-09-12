"""CODEF(https://codef.io) 개인 은행 계좌 조회 클라이언트.

흐름
1. client_id/secret 으로 OAuth2 토큰 발급
2. 은행 로그인 정보(비밀번호는 CODEF 공개키로 RSA 암호화)를 등록해 connectedId 발급
3. connectedId + 기관코드로 계좌목록/거래내역 조회

응답 본문은 URL 인코딩된 JSON 이라 unquote 후 파싱한다.
"""
from __future__ import annotations

import base64
import json
import time
from datetime import date, timedelta
from urllib.parse import unquote_plus

import requests

from ..config import Settings
from ..models import Account, Transaction
from .banks import bank_name

BASE_URLS = {
    "sandbox": "https://sandbox.codef.io",
    "demo": "https://development.codef.io",
    "api": "https://api.codef.io",
}
TOKEN_URL = "https://oauth.codef.io/oauth/token"
SUCCESS = "CF-00000"


class CodefError(RuntimeError):
    pass


def decode_body(text: str) -> dict:
    return json.loads(unquote_plus(text))


def encrypt_password(public_key_b64: str, password: str) -> str:
    """CODEF 계정 페이지의 RSA 공개키(DER, base64)로 PKCS#1 v1.5 암호화."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key = serialization.load_der_public_key(base64.b64decode(public_key_b64))
    return base64.b64encode(key.encrypt(password.encode("utf-8"), padding.PKCS1v15())).decode("ascii")


def classify_kind(deposit_code: str) -> str:
    """resAccountDeposit 코드 → 계좌 종류. 11 입출금, 12 예금, 13 적금, 14 신탁 등."""
    return {"11": "deposit", "12": "savings", "13": "savings", "14": "investment"}.get(deposit_code, "deposit")


class CodefClient:
    def __init__(self, client_id: str, client_secret: str, env: str = "sandbox", session: requests.Session | None = None):
        if env not in BASE_URLS:
            raise ValueError(f"CODEF_ENV 는 {list(BASE_URLS)} 중 하나여야 합니다")
        self.base = BASE_URLS[env]
        self.client_id = client_id
        self.client_secret = client_secret
        self.http = session or requests.Session()
        self._token: str | None = None
        self._token_exp = 0.0

    def token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        r = self.http.post(
            TOKEN_URL,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "scope": "read"},
            timeout=30,
        )
        if r.status_code != 200:
            raise CodefError(f"토큰 발급 실패 {r.status_code}: {r.text[:200]}")
        body = r.json()
        self._token = body["access_token"]
        self._token_exp = time.time() + int(body.get("expires_in", 3600))
        return self._token

    def post(self, path: str, body: dict) -> dict:
        r = self.http.post(
            self.base + path,
            headers={"Authorization": f"Bearer {self.token()}", "Content-Type": "application/json"},
            data=json.dumps(body),
            timeout=120,
        )
        data = decode_body(r.text)
        result = data.get("result", {})
        if result.get("code") != SUCCESS:
            raise CodefError(f"{path} 실패: {result.get('code')} {result.get('message')} {result.get('extraMessage','')}")
        return data.get("data", {})

    # ----- API -----
    def create_connected_id(self, logins: list[tuple[str, str, str]], public_key: str) -> str:
        accounts = [
            {
                "countryCode": "KR", "businessType": "BK", "clientType": "P",
                "organization": org, "loginType": "1",
                "id": user_id, "password": encrypt_password(public_key, password),
            }
            for org, user_id, password in logins
        ]
        data = self.post("/v1/account/create", {"accountList": accounts})
        failed = [e for e in data.get("errorList", []) if e.get("code") != SUCCESS]
        if failed:
            raise CodefError("계정 등록 실패: " + "; ".join(f"{e.get('organization')} {e.get('message')}" for e in failed))
        return data["connectedId"]

    def account_list(self, connected_id: str, org: str) -> dict:
        return self.post("/v1/kr/bank/p/account/account-list", {"organization": org, "connectedId": connected_id})

    def transaction_list(self, connected_id: str, org: str, account: str, start: str, end: str) -> list[dict]:
        data = self.post(
            "/v1/kr/bank/p/account/transaction-list",
            {"organization": org, "connectedId": connected_id, "account": account,
             "startDate": start, "endDate": end, "orderBy": "0"},
        )
        return data.get("resTrHistoryList", [])


# ----- 응답 → 공통 모델 변환 (테스트 가능하도록 순수 함수) -----

def _to_int(v) -> int:
    if v in (None, ""):
        return 0
    return int(float(str(v).replace(",", "")))


def parse_accounts(org: str, data: dict) -> list[Account]:
    out: list[Account] = []
    bank = bank_name(org)
    for item in data.get("resDepositTrust", []):
        number = item.get("resAccount", "")
        out.append(Account(
            id=f"codef:{org}:{number}", provider="codef", bank=bank,
            name=item.get("resAccountName") or item.get("resAccountNickName") or "계좌",
            number=item.get("resAccountDisplay") or number,
            kind=classify_kind(str(item.get("resAccountDeposit", "11"))),
            balance=_to_int(item.get("resAccountBalance")),
            currency=item.get("resAccountCurrency") or "KRW", org_code=org,
        ))
    for item in data.get("resFund", []):
        number = item.get("resAccount", "")
        out.append(Account(
            id=f"codef:{org}:{number}", provider="codef", bank=bank,
            name=item.get("resAccountName") or "펀드", number=item.get("resAccountDisplay") or number,
            kind="investment", balance=_to_int(item.get("resAccountBalance")), org_code=org,
        ))
    for item in data.get("resLoan", []):
        number = item.get("resAccount", "")
        out.append(Account(
            id=f"codef:{org}:{number}", provider="codef", bank=bank,
            name=item.get("resAccountName") or "대출", number=item.get("resAccountDisplay") or number,
            kind="loan", balance=-_to_int(item.get("resAccountBalance")), org_code=org,
        ))
    return out


def parse_transactions(account_id: str, rows: list[dict]) -> list[Transaction]:
    out: list[Transaction] = []
    for r in rows:
        d = str(r.get("resAccountTrDate", ""))
        t = str(r.get("resAccountTrTime", "")).ljust(6, "0")
        amount = _to_int(r.get("resAccountIn")) - _to_int(r.get("resAccountOut"))
        desc = " ".join(filter(None, (r.get("resAccountDesc1"), r.get("resAccountDesc2"),
                                      r.get("resAccountDesc3"), r.get("resAccountDesc4")))).strip()
        out.append(Transaction(
            account_id=account_id,
            date=f"{d[:4]}-{d[4:6]}-{d[6:8]}",
            time=f"{t[:2]}:{t[2:4]}:{t[4:6]}",
            description=desc or "(적요 없음)",
            amount=amount,
            balance_after=_to_int(r.get("resAfterTranBalance")) if r.get("resAfterTranBalance") not in (None, "") else None,
            source="codef",
        ))
    return out


class CodefProvider:
    """Settings 로 구성되는 상위 래퍼. connectedId 는 store.kv 에 보관해 재사용한다."""

    name = "codef"

    def __init__(self, settings: Settings, store=None, client: CodefClient | None = None):
        if not settings.codef_client_id or not settings.codef_client_secret:
            raise CodefError("CODEF_CLIENT_ID / CODEF_CLIENT_SECRET 이 필요합니다 (.env 참고)")
        self.settings = settings
        self.store = store
        self.client = client or CodefClient(settings.codef_client_id, settings.codef_client_secret, settings.codef_env)

    def connected_id(self) -> str:
        key = f"codef:{self.settings.codef_env}:connected_id"
        cid = self.store.kv_get(key) if self.store else None
        if cid:
            return cid
        if not self.settings.bank_logins:
            raise CodefError("CODEF_BANK_LOGINS 가 비어 있어 connectedId 를 만들 수 없습니다")
        if not self.settings.codef_public_key:
            raise CodefError("CODEF_PUBLIC_KEY 가 필요합니다")
        cid = self.client.create_connected_id(
            [(b.organization, b.user_id, b.password) for b in self.settings.bank_logins],
            self.settings.codef_public_key,
        )
        if self.store:
            self.store.kv_set(key, cid)
        return cid

    def organizations(self) -> list[str]:
        return sorted({b.organization for b in self.settings.bank_logins})

    def fetch_accounts(self) -> list[Account]:
        cid = self.connected_id()
        accounts: list[Account] = []
        for org in self.organizations():
            accounts.extend(parse_accounts(org, self.client.account_list(cid, org)))
        return accounts

    def fetch_transactions(self, accounts: list[Account], days: int = 31) -> list[Transaction]:
        cid = self.connected_id()
        end = date.today()
        start = end - timedelta(days=days)
        txs: list[Transaction] = []
        for a in accounts:
            if a.kind not in ("deposit", "savings"):
                continue
            number = a.id.split(":", 2)[2]
            rows = self.client.transaction_list(cid, a.org_code, number, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
            txs.extend(parse_transactions(a.id, rows))
        return txs
