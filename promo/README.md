# KICPA Assistant 홍보 영상

**결과물:** [`kicpa_assistant_promo.mp4`](kicpa_assistant_promo.mp4) · 1920×1080 · 30fps · 35.7초 · 128 BPM

## 브랜드 스토리

기능 소개 대신 **"회계사의 시간은 찾는 데가 아니라 판단하는 데 쓰여야 한다"**를 말합니다.

> **찾는 시간을, 판단하는 시간으로.** — KICPA Assistant

## 구성안

| 시간 | 박자 | 장면 | 텍스트 |
|---|---|---|---|
| 0:00–0:01.6 | 음악 전 | **후킹.** 새벽 타이핑 실사 영상 위로 PDF 찾기창에 "변동대가 추정치의 제약"을 입력하면 `0 / 0`이 뜨고 에러음이 납니다. | AM 2:47 · 412 / 1,284쪽 · **일치하는 항목이 없습니다** |
| 0:01.6–0:07 | 2박마다 쾅 | 검은 화면에 큰 글자 (키노트 스타일) | 새벽 2시 47분. / 기준서 1,284쪽. (숫자가 카운트업) / 찾는 건 / 단 한 문단. / 그런데, / 어디였더라? |
| 0:07–0:14 | 빌드업 | 타이핑 실사 위로 기준서·세법·판례 문서 창이 한 박자마다, 이어서 반 박자마다 쌓입니다. 스네어 롤과 라이저가 깔립니다. | 열고. / 또 열고. / 스크롤하고. / Ctrl + F. / … / 또. 또. |
| 0:14.3 | **1박 정적** | 완전한 암전과 무음 | |
| 0:14.7–0:22 | **드롭: 한 박자에 한 단어** | 단어마다 **앱의 실제 카테고리 카드**가 배경으로 나옵니다. | 물어보세요.(실제 입력창) / 일반 / 감사기준서 / K-IFRS / K-GAAP / 법령정보 / 국세·지방세 / 세법해석례 / 국세 판례 / 지방세 해석례 / 지방세 판례 / 전부, 한 곳에서. |
| 0:21–0:22 | | 카드 클로즈업에서 줌아웃하면 실제 "새 채팅" 화면이 나옵니다. | KICPA Assistant |
| 0:22–0:28 | 드롭 2 | **실제 앱 화면** 3종: 홈, 새 채팅, 대화 목록 | 고르고, 묻고, 답을 받는다. / 카테고리를 고르면, 그 기준으로 답합니다. / 대화는 이 기기에만 저장됩니다. |
| 0:28–0:31.6 | 드럼이 빠지고 필터 | 검은 화면, 느린 푸시인 | 당신은 회계사입니다. / 검색하는 사람이 아니라. |
| 0:31.6–끝 | 마지막 한 방 | 흰 플래시에 이어 브랜드 한 줄과 로고 | **찾는 시간을, 판단하는 시간으로.** + [K] KICPA Assistant |

앱 문구("그 기준으로 답합니다", "이 기기에만 저장됩니다")는 실제 화면에 있는 내용만 가져왔습니다.

## 음악

`make_audio.py`로 직접 합성했습니다. 샘플을 쓰지 않아 저작권 문제가 없습니다.
- 128 BPM, A단조. 오프닝은 서브 붐만, 빌드업은 4/4 킥과 16분 하이햇, 가속하는 스네어 롤, 노이즈 라이저로 구성했습니다.
- 드롭 직전 1박은 완전 무음입니다.
- 드롭은 Am9 – Fmaj7 – Cmaj7 – Em7 진행에 플럭 모티프, 사이드체인 서브, 2·4박 클랩을 얹었습니다.
- 엔딩은 C장조로 해결되고 긴 잔향으로 끝납니다.

## 다시 만들기

```bash
pip install numpy scipy pillow imageio-ffmpeg
cd promo
# 1) 실사 소스를 받아 30fps 프레임으로 추출 (아래 출처 참고)
FF=$(python3 -c "import imageio_ffmpeg as i;print(i.get_ffmpeg_exe())")
mkdir -p build/stock
$FF -i typing.webm -t 12 -vf fps=30 -q:v 3 build/stock/typing_%04d.jpg
# 2) 음악, 3) 영상
python3 make_audio.py
python3 render.py              # -> build/kicpa_assistant_promo.mp4
python3 render.py 3.2 15.0     # 특정 시점 스틸 미리보기
```

타이밍은 모두 `timeline.py`의 박자 그리드 하나로 관리합니다. BPM이나 구간을 바꾸면 음악과 영상이 함께 바뀝니다.

## 출처

- **앱 화면:** KICPA Assistant 실제 스크린샷 (`assets/screens/`)
- **실사 영상:** "Hunt and peck typing — Monkeytype benchmark", Wikimedia Commons, **CC BY 4.0**.
  https://commons.wikimedia.org/wiki/File:Hunt_and_peck_typing_%E2%80%94_Monkeytype_benchmark.webm
  (색 보정과 밝기 조정 후 사용. 외부에 게시할 때는 위 페이지의 저작자명을 함께 표기하세요.)
- **폰트:** Pretendard (SIL Open Font License 1.1)
