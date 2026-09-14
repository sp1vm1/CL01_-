#!/usr/bin/env python3
"""수원시 행사 수집기 — 공식 경로만 사용한다(스크래핑 금지).

  ① 한국관광공사 TourAPI 행사/축제 (areaCode 31=경기, sigunguCode 13=수원)
       env TOURAPI_KEY  (data.go.kr 에서 발급한 일반 인증키, 디코딩된 값)
  ② 인스타그램 공식 계정 — Meta Graph API Business Discovery
       env IG_ACCESS_TOKEN, IG_USER_ID (자기 비즈니스 계정 ID)
       env IG_ACCOUNTS   (조회할 공개 비즈니스 계정, 기본 "suwon_city,suwoni_official,suwon_sudc")
  둘 다 실패하면 exit 0 으로 빈 결과와 원인만 출력하므로, 호출자는 뉴스 검색으로 대체하면 된다.

사용:  python3 suwon_events.py [--days 21] > suwon_raw.json
"""
import json, os, sys, urllib.parse, urllib.request, datetime as dt

OUT = {"generated": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds"),
       "tourapi": [], "instagram": {}, "errors": []}

def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "brief-suwon/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def days_arg():
    a = sys.argv[1:]
    return int(a[a.index("--days") + 1]) if "--days" in a else 21

# ── ① TourAPI ──────────────────────────────────────────────────────────
def tourapi():
    key = os.environ.get("TOURAPI_KEY")
    if not key:
        OUT["errors"].append("tourapi: TOURAPI_KEY 미설정 — data.go.kr 에서 '한국관광공사_국문 관광정보 서비스' 키 발급 필요")
        return
    today = dt.date.today()
    start = (today - dt.timedelta(days=days_arg())).strftime("%Y%m%d")
    q = urllib.parse.urlencode({
        "serviceKey": key, "MobileOS": "ETC", "MobileApp": "brief", "_type": "json",
        "numOfRows": 60, "pageNo": 1, "arrange": "C",
        "eventStartDate": start, "areaCode": 31, "sigunguCode": 13,
    }, safe="=%")
    last = None
    for ver in ("KorService2/searchFestival2", "KorService1/searchFestival1"):
        try:
            d = get(f"https://apis.data.go.kr/B551011/{ver}?{q}")
            items = (((d.get("response") or {}).get("body") or {}).get("items") or {}).get("item") or []
            if isinstance(items, dict): items = [items]
            for it in items:
                OUT["tourapi"].append({
                    "title": it.get("title"), "start": it.get("eventstartdate"), "end": it.get("eventenddate"),
                    "place": it.get("addr1"), "tel": it.get("tel"), "image": it.get("firstimage"),
                    "contentid": it.get("contentid"),
                })
            return
        except Exception as e:  # 도메인 차단이면 URLError(connect_rejected)
            last = f"{ver}: {type(e).__name__}: {e}"
    OUT["errors"].append("tourapi: " + (last or "unknown"))

# ── ② Instagram Business Discovery ─────────────────────────────────────
def instagram():
    tok, uid = os.environ.get("IG_ACCESS_TOKEN"), os.environ.get("IG_USER_ID")
    if not (tok and uid):
        OUT["errors"].append("instagram: IG_ACCESS_TOKEN/IG_USER_ID 미설정 — Meta 개발자 앱 + 페이스북 페이지에 연결된 IG 비즈니스 계정 필요")
        return
    accounts = [a.strip() for a in os.environ.get("IG_ACCOUNTS", "suwon_city,suwoni_official,suwon_sudc").split(",") if a.strip()]
    for acc in accounts:
        fields = f"business_discovery.username({acc}){{name,username,media.limit(12){{caption,permalink,timestamp,media_type}}}}"
        url = f"https://graph.facebook.com/v19.0/{uid}?fields={urllib.parse.quote(fields, safe='(){},.')}&access_token={urllib.parse.quote(tok)}"
        try:
            d = get(url)
            bd = d.get("business_discovery") or {}
            OUT["instagram"][acc] = [
                {"caption": (m.get("caption") or "")[:600], "permalink": m.get("permalink"),
                 "timestamp": m.get("timestamp"), "type": m.get("media_type")}
                for m in ((bd.get("media") or {}).get("data") or [])
            ]
        except Exception as e:
            OUT["errors"].append(f"instagram {acc}: {type(e).__name__}: {e}")

if __name__ == "__main__":
    tourapi()
    instagram()
    json.dump(OUT, sys.stdout, ensure_ascii=False, indent=1)
    print()
