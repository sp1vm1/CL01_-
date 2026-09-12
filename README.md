# 통합 계좌 조회 + 가계부

내가 가진 모든 은행 계좌의 잔액과 거래내역을 한곳에 모아 보고, 월별 수입·지출을 분석하는 프로그램입니다.

- **실시간 조회**: [CODEF](https://codef.io) API로 은행 계좌 잔액·거래내역을 주기적으로 가져옵니다. 개인 개발자가 가입해 쓸 수 있는 유일한 금융 데이터 API입니다. (금융결제원 오픈뱅킹·마이데이터 API는 사업자 전용)
- **뱅크샐러드 가져오기**: 뱅크샐러드 "내보내기" 엑셀을 읽어 과거 거래와 계좌 스냅샷을 채웁니다.
- **모의 모드**: 자격증명 없이도 화면과 리포트를 바로 볼 수 있습니다.
- **자동 분류**: 키워드 규칙으로 카테고리를 매기고, 뱅크샐러드가 틀리게 잡던 항목(흥국·라이나 보험료가 "카페/여가"로 분류되는 등)을 바로잡습니다.
- **중복 제거**: 같은 시각·같은 금액·같은 가맹점이 두 결제수단으로 두 번 잡힌 페이 결제를 집계에서 한 번만 셉니다.
- **웹 대시보드**: 잔액 합계, 월 리포트, 두 달 비교. "지금 새로고침" 버튼과 자동 갱신.

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env      # 필요한 값 채우기
```

## 빠른 시작 (모의 데이터)

```bash
python -m ledger.cli sync          # LEDGER_PROVIDER=mock 기본값
python -m ledger.cli balances
python -m ledger.cli web           # http://127.0.0.1:5000
```

## 뱅크샐러드 엑셀 가져오기

뱅크샐러드 앱 → 설정 → 내보내기 로 받은 xlsx 파일을 넣습니다. 여러 번 실행해도 거래가 중복되지 않습니다.

```bash
python -m ledger.cli import-banksalad ~/Downloads/뱅크샐러드.xlsx
python -m ledger.cli report 2026-09 --provider banksalad
python -m ledger.cli compare 2026-08 2026-09 --provider banksalad
```

## CODEF 실시간 연동

1. https://codef.io 에서 가입 후 **샌드박스** 또는 **데모** 키(client id / secret)와 **RSA 공개키**를 확인합니다.
   - sandbox: 고정 더미 데이터, 무료. 연동 흐름 확인용
   - demo: 실제 은행 데이터, 무료지만 호출 한도 있음. 개인 가계부 용도면 충분
   - api: 운영, 유료
2. `.env` 를 채웁니다.

```
LEDGER_PROVIDER=codef
CODEF_ENV=demo
CODEF_CLIENT_ID=...
CODEF_CLIENT_SECRET=...
CODEF_PUBLIC_KEY=...
CODEF_BANK_LOGINS=0004:국민은행아이디:비밀번호;0088:신한아이디:비밀번호;0092:토스뱅크아이디:비밀번호
LEDGER_REFRESH_MINUTES=10
```

   기관코드는 `ledger/providers/banks.py` 에 있습니다. 은행 로그인은 인터넷뱅킹 ID/PW 방식(loginType 1)입니다. 공동인증서 방식이 필요하면 CODEF 문서의 loginType 0 파라미터를 `codef.py` 의 `create_connected_id` 에 추가하면 됩니다.
3. 첫 `sync` 에서 CODEF 에 계정을 등록해 `connectedId` 를 받아 DB 에 저장합니다. 이후에는 비밀번호를 다시 보내지 않습니다.

```bash
python -m ledger.cli sync --days 31
python -m ledger.cli web
```

`web` 은 `LEDGER_REFRESH_MINUTES` 마다 자동으로 다시 조회합니다. CODEF 는 호출 단위로 과금·한도가 있으므로 운영 키에서는 주기를 넉넉히 잡으세요.

## 분류 규칙 추가

프로젝트 루트에 `rules.json` 을 두면 기본 규칙보다 먼저 적용됩니다.

```json
[
  {"pattern": "수원제일교회", "category": "경조/선물", "subcategory": "헌금"},
  {"pattern": "대주회계", "category": "급여", "subcategory": "급여"}
]
```

## 구조

```
ledger/
  cli.py               명령줄
  web.py               Flask 대시보드 (/, /report, /compare, /api/balances)
  sync.py              공급자 → DB 동기화, 뱅크샐러드 가져오기
  report.py            잔액 요약, 월 리포트, 비교
  categorize.py        규칙 기반 분류, 페이 중복 키
  db.py                SQLite (accounts, transactions, balance_snapshots, sync_log)
  models.py            Account / Transaction
  providers/codef.py   CODEF 클라이언트 (토큰, connectedId, 계좌목록, 거래내역)
  providers/mock.py    모의 데이터
  importers/banksalad.py
tests/                 pytest
```

## 보안

- `.env`, `data/`, `*.xlsx`, `*.db` 는 `.gitignore` 에 있습니다. 은행 비밀번호와 거래내역은 절대 저장소에 올리지 마세요.
- 은행 비밀번호는 CODEF 공개키로 암호화되어 CODEF 로만 전송되고, 로컬 DB 에는 `connectedId` 만 남습니다.
- 대시보드는 기본으로 127.0.0.1 에만 바인딩됩니다. 외부에 열 때는 앞에 인증을 붙이세요.

## 테스트

```bash
python -m pytest -q
```
