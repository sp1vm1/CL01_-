import json
from urllib.parse import quote_plus

from ledger.providers.codef import decode_body, parse_accounts, parse_transactions


def test_decode_url_encoded_body():
    payload = {"result": {"code": "CF-00000"}, "data": {"resDepositTrust": []}}
    assert decode_body(quote_plus(json.dumps(payload))) == payload


def test_parse_accounts_maps_deposit_fund_loan():
    data = {
        "resDepositTrust": [{"resAccount": "1234567890", "resAccountDisplay": "123-45-****90",
                             "resAccountName": "KB Star*t통장", "resAccountBalance": "58204", "resAccountDeposit": "11"}],
        "resFund": [{"resAccount": "F1", "resAccountName": "펀드", "resAccountBalance": "7344276"}],
        "resLoan": [{"resAccount": "L1", "resAccountName": "신용대출", "resAccountBalance": "1000000"}],
    }
    accts = parse_accounts("0004", data)
    assert [a.kind for a in accts] == ["deposit", "investment", "loan"]
    assert accts[0].id == "codef:0004:1234567890" and accts[0].balance == 58204 and accts[0].bank == "KB국민은행"
    assert accts[2].balance == -1000000


def test_parse_transactions_sign_and_hash_stable():
    rows = [
        {"resAccountTrDate": "20260912", "resAccountTrTime": "103141", "resAccountOut": "12500", "resAccountIn": "",
         "resAfterTranBalance": "45704", "resAccountDesc1": "체크카드", "resAccountDesc3": "울라(OOLA)"},
        {"resAccountTrDate": "20260904", "resAccountTrTime": "1037", "resAccountOut": "0", "resAccountIn": "3916770",
         "resAfterTranBalance": "4000000", "resAccountDesc3": "대주회계급여"},
    ]
    a = parse_transactions("codef:0004:1", rows)
    b = parse_transactions("codef:0004:1", rows)
    assert a[0].amount == -12500 and a[0].date == "2026-09-12" and a[0].time == "10:31:41"
    assert a[1].amount == 3916770 and a[1].time == "10:37:00"
    assert [t.id for t in a] == [t.id for t in b]
