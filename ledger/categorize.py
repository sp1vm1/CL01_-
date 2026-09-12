"""키워드 규칙 기반 자동 분류.

규칙은 위에서부터 첫 매칭이 이긴다. 뱅크샐러드가 틀리게 잡던 항목(흥국·라이나 보험료 등)을 바로잡는
규칙이 앞쪽에 있다. 사용자가 rules.json 을 두면 그 규칙이 기본 규칙보다 먼저 적용된다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# (정규식, 대분류, 소분류)
DEFAULT_RULES: list[tuple[str, str, str]] = [
    # 보험료 (뱅크샐러드가 카페/여가로 오분류하던 건 포함)
    (r"흥국|LINA|라이나|ABL생명|메리츠|삼성화|KDB생명|동양생명|한화생명|교보생명|현대해상|DB손해", "보험", "보험료"),
    # 급여
    (r"급여|월급|상여", "급여", "급여"),
    # 저축/투자
    (r"청년도약|청약|적금|IRP|연금저축|증권|투자", "저축/투자", "납입"),
    # 고정비
    (r"KT통신|SKT|LG유플|LGU\+|통신요금|SKYLIFE|넷플릭스|유튜브|멜론|스포티파이|구독", "주거/통신", "통신/구독"),
    (r"관리비|월세|전기요금|가스요금|수도요금|도시가스", "주거/통신", "주거"),
    # 헌금/기부
    (r"십일조|헌금|교회|기부|후원|휴먼인러브", "경조/선물", "기부/헌금"),
    # 의료
    (r"치과|병원|의원|약국|상담센터|한의원|플란트", "의료/건강", "병원/약국"),
    # 교통
    (r"한국철도|코레일|SRT|티머니|캐시비|버스|지하철|택시|카카오T|고속도로|하이패스", "교통", "대중교통"),
    (r"주차|주유|SK에너지|GS칼텍스|S-OIL|현대오일|세차", "자동차", "주유/주차"),
    # 식비
    (r"배민|배달의민족|요기요|쿠팡이츠", "식비", "배달"),
    (r"맥도날드|버거킹|롯데리아|맘스터치|KFC|서브웨이", "식비", "패스트푸드"),
    (r"치킨|피자|설렁탕|식당|국밥|김밥|분식|고기|초밥|파스타|OOLA|울라|휴게소", "식비", "외식"),
    (r"스타벅스|투썸|이디야|메가커피|컴포즈|빽다방|커피|카페|베이커리|파리바게뜨|뚜레쥬르", "카페/간식", "커피/음료"),
    # 생활
    (r"CU|씨유|GS25|지에스25|세븐일레븐|이마트24|편의점", "생활", "편의점"),
    (r"다이소|이마트|홈플러스|롯데마트|코스트코|마트", "생활", "마트/생필품"),
    (r"프린트|세탁|미용실|이발", "생활", "생활서비스"),
    # 쇼핑
    (r"쿠팡|알리|ALIPAY|11번가|G마켓|옥션|네이버페이|SSG|무신사|KREAM|Apple|앱스토어|Google Play|주식회사 카카오", "온라인쇼핑", "인터넷쇼핑"),
    (r"스타필드|타임빌라스|백화점|아울렛|올리브영|레드에너지|화장품", "패션/쇼핑", "오프라인쇼핑"),
    # 여가
    (r"스터디카페|개인전|전시|영화|CGV|메가박스|롯데시네마|학원|리조트|호텔|숙박|항공", "문화/여가", "여가"),
    # 이체/카드대금 (지출 집계에서 제외되는 범주)
    (r"카드출금|카드대금|신한카드|KB카드|삼성카드|현대카드|롯데카드|우리카드|하나카드|비씨카드", "이체", "카드대금"),
    (r"네이버페이충전|카카오페이|토스머니|페이코|충전", "이체", "페이충전"),
    (r"이자$|^이자|체크할인|캐시백|환급", "금융수입", "이자/할인"),
]

# 지출/수입 합계에서 제외할 대분류
TRANSFER_CATEGORIES = {"이체", "내계좌이체", "카드대금", "저축/투자"}


def load_rules(path: str | Path | None = "rules.json") -> list[tuple[re.Pattern, str, str]]:
    rules: list[tuple[str, str, str]] = []
    if path and Path(path).exists():
        for r in json.loads(Path(path).read_text(encoding="utf-8")):
            rules.append((r["pattern"], r["category"], r.get("subcategory", "")))
    rules.extend(DEFAULT_RULES)
    return [(re.compile(p, re.IGNORECASE), c, s) for p, c, s in rules]


def categorize(description: str, amount: int, rules=None) -> tuple[str, str]:
    rules = rules if rules is not None else load_rules()
    for pat, cat, sub in rules:
        if pat.search(description):
            if cat == "급여" and amount < 0:  # '급여' 단어가 있어도 출금이면 급여가 아님
                continue
            return cat, sub
    return ("기타수입" if amount > 0 else "미분류", "")


def is_transfer(category: str) -> bool:
    return category in TRANSFER_CATEGORIES


def dedupe_key(t) -> tuple:
    """같은 시각·같은 금액·같은 가맹점이 다른 결제수단으로 두 번 잡힌 건(페이 중복)을 찾기 위한 키."""
    return (t["date"], t["time"], t["amount"], re.sub(r"\s+", "", t["description"]))
