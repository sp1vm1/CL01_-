#!/usr/bin/env python3
# brief.html 조립 스크립트
# 기존 아티팩트 소스(Read 도구로 전 줄 확인 완료)에서 구조와 archive를 바이트 그대로 이어붙이고
# DATA의 periods 부분만 새로 작성한 블록으로 교체한다.
import io, sys

SRC = "/root/.claude/projects/-home-user-CL01--/b6abbd8b-4a97-56c3-b66f-210a10180235/tool-results/artifact-7466051b-1789250561-17e1.html"
OUT = "/home/user/CL01_-/brief.html"
NEWDATA = "/home/user/CL01_-/newdata.js"

with io.open(SRC, encoding="utf-8") as f:
    L = f.read().split("\n")          # L[0] == 파일 1행
def seg(a, b):                         # 1-기준, 양끝 포함
    return L[a-1:b]

# ── 경계 검증 (어긋나면 즉시 중단) ────────────────────────────
def must(cond, msg):
    if not cond:
        sys.exit("BOUNDARY FAIL: " + msg)

must(L[0].startswith("<!doctype html>"), "line1 doctype")
must(L[1].startswith("<title>6시 브리핑"), "line2 title")
must("==== DATA:BEGIN ====" in L[232], "line233 DATA:BEGIN")
must(L[233].startswith("const DATA = {"), "line234 const DATA")
must(L[241].strip() == "periods: {", "line242 periods")
must(L[242].strip() == "daily: {", "line243 daily")
must(L[677].strip() == "},", "line678 daily close")
must(L[678].strip() == "weekly: {", "line679 weekly")
must(L[956].strip() == "},", "line957 weekly close")
must(L[957].strip() == "monthly: {", "line958 monthly")
must(L[1058].strip() == "}", "line1059 monthly close")
must(L[1060].strip() == "};", "line1061 DATA close")
must(L[1061].startswith("DATA.archive = {"), "line1062 archive init")
must(L[1062].startswith('DATA.archive.daily["2026-09-04"]'), "line1063 archive daily start")
must(L[4515].strip() == "};", "line4516 archive daily end")
must(L[4516].startswith('DATA.archive.weekly["2026-08-10"]'), "line4517 archive weekly start")
must(L[4627].strip() == "};", "line4628 archive weekly end")
must(L[4628].startswith('DATA.archive.weekly["2026-08-31"]'), "line4629 weekly ref")
must(L[4629].startswith('DATA.archive.monthly["2026-07"]'), "line4630 monthly ref")
must(L[4630].startswith('DATA.archive.daily["2026-09-12"]'), "line4631 daily ref")
must("==== DATA:END ====" in L[4631], "line4632 DATA:END")
must(L[4632].startswith("const CATS"), "line4633 CATS")
must(L[4888].strip() == "</script>", "line4889 script close")

# ── 조각 ────────────────────────────────────────────────────
head      = seg(2, 233)      # <title> ~ DATA:BEGIN  (doctype 래퍼는 버림)
old_daily = seg(243, 678)    # 기존 periods.daily (2026-09-12)
old_weekly= seg(679, 957)    # 기존 periods.weekly (2026-08-31 주)
monthly   = seg(958, 1059)   # periods.monthly (2026-07) — 그대로 재사용
arch_init = seg(1062, 1062)
arch_daily= seg(1063, 4516)  # 09-04 ~ 09-11 리터럴
arch_wk   = seg(4517, 4628)  # 2026-08-10 주 리터럴
data_end  = seg(4632, 4632)
renderer  = seg(4633, 4889)  # const CATS ~ </script>

# 기존 periods.daily / periods.weekly 를 archive 리터럴로 풀어서 보존
d = list(old_daily); d[0] = 'DATA.archive.daily["2026-09-12"] = {'; d[-1] = '};'
w = list(old_weekly); w[0] = 'DATA.archive.weekly["2026-08-31"] = {'; w[-1] = '};'

with io.open(NEWDATA, encoding="utf-8") as f:
    newdata = f.read().rstrip("\n").split("\n")

# ── 렌더러 패치 없음 ────────────────────────────────────────
# 2026-09-15 기준 원본 아티팩트에는 수원 탭(HIDDEN_CATS·eventCard·.tab-more)과
# FORMAT NOTE 7·8항이 이미 들어 있다. 따라서 여기서 렌더러를 손대면 안 된다.
# 수원 탭은 CATS가 아니라 HIDDEN_CATS에 있어야 하고(기본 숨김), 탭 줄 끝 '···'
# 버튼으로만 펼쳐진다. 원본에서 잘라온 renderer 조각을 그대로 붙여 쓴다.

out = []
out += head
out += newdata                # const DATA = { updatedAt, indices, periods{daily,weekly,
out += monthly                #   monthly(기존 그대로) }
out += ["  }", "};"]          # periods 닫기, DATA 닫기
out += arch_init
out += arch_daily
out += d                      # 2026-09-12 리터럴 (직전 일간 보존)
out += arch_wk
out += w                      # 2026-08-31 리터럴 (직전 주간 보존)
out += ['DATA.archive.monthly["2026-07"] = DATA.periods.monthly;']
out += ['DATA.archive.daily["2026-09-13"] = DATA.periods.daily;']
out += ['DATA.archive.weekly["2026-09-07"] = DATA.periods.weekly;']
out += data_end
out += renderer

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print("OK lines=%d bytes=%d" % (len(out), sum(len(x)+1 for x in out)-1))
print("tail:", repr(out[-1]))
