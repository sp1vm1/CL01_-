"""Renders the KICPA Assistant promo, frame by frame, locked to the soundtrack's beat grid.

Needs: build/soundtrack.wav (make_audio.py) and build/stock/typing_*.jpg (see README).
Output: build/kicpa_assistant_promo.mp4 (1920x1080, 30 fps)
"""
import glob
import math
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

from timeline import (W, H, FPS, DURATION, BEAT, HOOK, beat_of, t_of,
                      A_OPEN, B_BUILD, STOP, C_DROP, D_APP, E_PIVOT, F_END)

BLUE = (3, 80, 254)
INK = (14, 16, 22)
WHITE = (255, 255, 255)
BRAND_LINE = ("찾는 시간을,", "판단하는 시간으로.")

# ---------------- assets ----------------
_fonts = {}


def font(size, weight="Black"):
    key = (int(size), weight)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(f"assets/fonts/Pretendard-{weight}.otf", int(size))
    return _fonts[key]


SCREENS = {n: Image.open(f"assets/screens/{n}.jpg").convert("RGB") for n in ("home", "newchat", "sidebar")}
K = 1080 / 923  # screenshots were measured at 923px wide


def rounded(im, r):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), r, fill=255)
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def crop_card(col, row):
    cols = [(45, 450), (473, 878)]
    rows = [(925, 1095), (1120, 1290), (1313, 1485), (1507, 1680), (1702, 1873)]
    (x0, x1), (y0, y1) = cols[col], rows[row]
    box = (int(x0 * K) + 2, int(y0 * K) + 2, int(x1 * K) - 2, int(y1 * K) - 2)
    return rounded(SCREENS["newchat"].crop(box), 34)


# Drop words, each paired with the real category card it names (one per beat)
DROP = [
    ("일반", crop_card(0, 0)),
    ("감사기준서", crop_card(1, 0)),
    ("K-IFRS", crop_card(0, 1)),
    ("K-GAAP", crop_card(1, 1)),
    ("법령정보", crop_card(0, 2)),
    ("국세·지방세", crop_card(1, 2)),
    ("세법해석례", crop_card(0, 3)),
    ("국세 판례", crop_card(1, 3)),
    ("지방세 해석례", crop_card(0, 4)),
    ("지방세 판례", crop_card(1, 4)),
]
INPUT_BAR = rounded(SCREENS["home"].crop((int(30 * K) + 2, int(1690 * K) + 2, int(893 * K) - 2, int(1895 * K) - 2)), 60)


def phone(name, height=940):
    scr = SCREENS[name]
    scr = scr.crop((0, 110, scr.width, scr.height))  # drop the carrier status bar
    bez = 16
    sh = height - 2 * bez
    sw = int(scr.width * sh / scr.height)
    scr = scr.resize((sw, sh), Image.LANCZOS)
    body = Image.new("RGBA", (sw + 2 * bez, height), (0, 0, 0, 0))
    ImageDraw.Draw(body).rounded_rectangle((0, 0, body.width - 1, height - 1), 62, fill=(18, 18, 20, 255),
                                           outline=(70, 72, 80, 255), width=3)
    body.alpha_composite(rounded(scr, 48), (bez, bez))
    return body


PHONES = {n: phone(n) for n in SCREENS}

STOCK = sorted(glob.glob("build/stock/typing_*.jpg"))
_stock_cache = {}


def stock_frame(t, tint=(10, 30, 90), bright=0.42):
    if not STOCK:
        return Image.new("RGB", (W, H), (8, 10, 18))
    i = int(t * FPS) % len(STOCK)
    if i not in _stock_cache:
        im = Image.open(STOCK[i]).convert("RGB").resize((W, H))
        im = ImageEnhance.Color(im).enhance(0.25)
        im = ImageEnhance.Brightness(im).enhance(bright)
        im = Image.blend(im, Image.new("RGB", (W, H), tint), 0.35)
        if len(_stock_cache) > 40:
            _stock_cache.clear()
        _stock_cache[i] = im
    return _stock_cache[i].copy()


# ---------------- helpers ----------------
def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def punch(dt, amt=0.14, tau=0.07):
    """Scale that slams in on a beat and settles."""
    return 1 + amt * math.exp(-max(dt, 0) / tau)


def text(d, xy, s, size, fill=WHITE, weight="Black", anchor="mm", stroke=0, stroke_fill=(0, 0, 0)):
    d.text(xy, s, font=font(size, weight), fill=fill, anchor=anchor,
           stroke_width=stroke, stroke_fill=stroke_fill)


def paste_scaled(base, im, center, scale, alpha=1.0):
    w, h = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    im2 = im.resize((w, h), Image.BILINEAR)
    if alpha < 1:
        a = im2.getchannel("A").point(lambda v: int(v * alpha))
        im2.putalpha(a)
    base.alpha_composite(im2, (int(center[0] - w / 2), int(center[1] - h / 2)))


def shadow_under(base, box, radius=40, blur=30, opacity=120):
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(box, radius, fill=(0, 0, 0, opacity))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def doc_window(title, w=760, h=480, seed=0):
    r = np.random.default_rng(seed)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=(245, 246, 250, 255), outline=(200, 204, 214, 255), width=2)
    d.rounded_rectangle((0, 0, w - 1, 56), 18, fill=(226, 229, 238, 255))
    d.rectangle((0, 38, w - 1, 56), fill=(226, 229, 238, 255))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((20 + i * 26, 20, 36 + i * 26, 36), fill=c)
    d.text((110, 28), title, font=font(24, "SemiBold"), fill=(60, 64, 76), anchor="lm")
    y = 90
    while y < h - 30:
        n = r.integers(3, 7)
        for j in range(n):
            ll = r.uniform(0.55, 1.0) if j < n - 1 else r.uniform(0.2, 0.6)
            d.rounded_rectangle((40, y, 40 + int((w - 80) * ll), y + 11), 5, fill=(196, 200, 212, 255))
            y += 22
        y += 18
    return im


DOCS = [doc_window(t, seed=i) for i, t in enumerate([
    "감사기준서 700 — 재무제표에 대한 의견형성과 보고.pdf",
    "K-IFRS 제1115호 — 고객과의 계약에서 생기는 수익.pdf",
    "K-IFRS 제1109호 — 금융상품.pdf",
    "일반기업회계기준 제6장.pdf",
    "법인세법 시행령.hwp",
    "부가가치세법 기본통칙.pdf",
    "국세 해석례 모음_2025.pdf",
    "조세심판원 결정례.pdf",
    "지방세법 운영예규.pdf",
    "감사기준서 570 — 계속기업.pdf",
    "K-IFRS 제1116호 — 리스.pdf",
    "법인세 판례 요약.xlsx",
    "(최종)(진짜최종) 검토메모.docx",
    "K-IFRS 제1036호 — 자산손상.pdf",
])]


# ---------------- scenes ----------------
def scene_hook(t):
    """0 ~ 1.6s: 2:47 AM, typing, Ctrl+F on a 1,284-page standard — no results."""
    base = stock_frame(t + 2.0, tint=(5, 18, 60), bright=0.5).convert("RGBA")
    zoom = 1 + 0.04 * t
    d = ImageDraw.Draw(base, "RGBA")
    # search overlay, like a PDF viewer's find bar
    query = "변동대가 추정치의 제약"
    typed = query[: int(len(query) * min(1, t / 0.75))]
    bw, bh = int(1100 * zoom), int(130 * zoom)
    cx, cy = W // 2, int(H * 0.45)
    shake = 0
    if 0.95 <= t < 1.25:
        shake = int(18 * math.sin((t - 0.95) * 90) * math.exp(-(t - 0.95) / 0.1))
    x0, y0 = cx - bw // 2 + shake, cy - bh // 2
    shadow_under(base, (x0, y0, x0 + bw, y0 + bh), 30, 25, 160)
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), int(28 * zoom), fill=(250, 250, 252, 245))
    mx, my, mr = x0 + 62 * zoom, cy - 6 * zoom, 18 * zoom
    d.ellipse((mx - mr, my - mr, mx + mr, my + mr), outline=(120, 124, 136), width=int(6 * zoom))
    d.line((mx + mr * 0.7, my + mr * 0.7, mx + mr * 1.6, my + mr * 1.6), fill=(120, 124, 136), width=int(7 * zoom))
    cursor = "|" if int(t * 6) % 2 == 0 and t < 0.95 else ""
    text(d, (x0 + 120 * zoom, cy), typed + cursor, 54 * zoom, INK, "SemiBold", "lm")
    if t >= 0.95:
        text(d, (x0 + bw - 50 * zoom, cy), "0 / 0", 54 * zoom, (230, 40, 40), "Black", "rm")
        a = int(255 * ease_out((t - 0.95) / 0.08))
        text(d, (cx + shake, y0 + bh + 110 * zoom), "일치하는 항목이 없습니다", 76 * zoom, (255, 80, 80, a), "ExtraBold")
    # context: clock + page counter
    text(d, (80, 70), "AM 2:47", 44, (255, 255, 255, 210), "Bold", "lm")
    text(d, (W - 80, 70), "412 / 1,284 쪽", 40, (255, 255, 255, 170), "SemiBold", "rm")
    return base


OPEN_LINES = ["새벽 2시 47분.", "기준서 1,284쪽.", "찾는 건", "단 한 문단.", "그런데,", "어디였더라?"]


def scene_open(b):
    base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(base, "RGBA")
    i = min(int((b - A_OPEN) // 2), len(OPEN_LINES) - 1)
    dt = (b - A_OPEN - 2 * i) * BEAT
    s = OPEN_LINES[i]
    if i == 1:  # the page count rolls up
        n = int(1284 * ease_out(dt / 0.35))
        s = f"기준서 {n:,}쪽."
    size = 170 * punch(dt, 0.1, 0.06)
    text(d, (W / 2, H / 2), s, size)
    return base


BUILD_LINES = {12: "열고.", 14: "또 열고.", 16: "스크롤하고.", 18: "Ctrl + F.", 20: "또 Ctrl + F.", 22: "다시 처음부터.",
               24: "열고.", 24.5: "찾고.", 25: "열고.", 25.5: "찾고.", 26: "또.", 26.5: "또."}


def scene_build(b, t):
    base = stock_frame(t).convert("RGBA")
    rel = b - B_BUILD
    # a new document window slams in every beat, then every half beat
    stamps = [k for k in np.arange(0, 12, 1.0)] + [k for k in np.arange(12, STOP - B_BUILD, 0.5)]
    shown = [s for s in stamps if s <= rel]
    r = np.random.default_rng(3)
    pos = [(r.uniform(260, W - 260), r.uniform(220, H - 200), r.uniform(0.75, 1.05)) for _ in stamps]
    for j, s in enumerate(shown):
        x, y, sc = pos[j]
        dt = (rel - s) * BEAT
        sc *= punch(dt, 0.08, 0.05)
        im = DOCS[j % len(DOCS)]
        base.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 40)))
        paste_scaled(base, im, (x, y), sc)
    keys = sorted(k for k in BUILD_LINES if k <= b)
    if keys:
        k = keys[-1]
        dt = (b - k) * BEAT
        base.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 120)))
        size = 190 * punch(dt, 0.1, 0.05)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        text(ImageDraw.Draw(sh), (W / 2, H / 2 + 8), BUILD_LINES[k], size, (0, 0, 0, 230))
        base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(22)))
        text(ImageDraw.Draw(base, "RGBA"), (W / 2, H / 2), BUILD_LINES[k], size)
    return base


def scene_drop(b):
    rel = b - C_DROP
    k = int(rel)
    dt = (rel - k) * BEAT
    if k == 0:  # "물어보세요." + the real input bar
        base = Image.new("RGBA", (W, H), BLUE + (255,))
        d = ImageDraw.Draw(base, "RGBA")
        text(d, (W / 2, H * 0.36), "물어보세요.", 190 * punch(dt, 0.16, 0.06))
        paste_scaled(base, INPUT_BAR, (W / 2, H * 0.72), 1.05 * punch(dt, 0.06, 0.08))
        if dt < 0.07:
            base.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - dt / 0.07)))))
        return base
    if 1 <= k <= len(DROP):
        word, card = DROP[k - 1]
        schemes = [(BLUE, WHITE), (INK, WHITE), ((244, 245, 250), INK)]
        bg, fg = schemes[(k - 1) % 3]
        base = Image.new("RGBA", (W, H), bg + (255,))
        d = ImageDraw.Draw(base, "RGBA")
        text(d, (W / 2, H * 0.34), word, 210 * punch(dt, 0.14, 0.05), fg)
        sc = 1.25 * punch(dt, 0.1, 0.07) + 0.08 * dt
        cx, cy = W / 2, H * 0.72
        shadow_under(base, (cx - card.width * sc / 2, cy - card.height * sc / 2 + 20,
                            cx + card.width * sc / 2, cy + card.height * sc / 2 + 20), 40, 30, 90)
        paste_scaled(base, card, (cx, cy), sc)
        return base
    # 11..15: "한 곳에서." then the real category sheet pulls back into the phone
    base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(base, "RGBA")
    if k <= 12:
        dt = (rel - 11) * BEAT
        text(d, (W / 2, H / 2), "전부, 한 곳에서.", 200 * punch(dt, 0.12, 0.06))
        return base
    p = ease_out((rel - 13) / 1.2)
    ph = PHONES["newchat"]
    sc = 2.4 - 1.4 * p
    cy = H / 2 + (1 - p) * -600
    paste_scaled(base, ph, (W * (0.5 + 0.18 * p), cy + (1 - p) * 250), sc)
    d = ImageDraw.Draw(base, "RGBA")
    a = int(255 * ease_out((rel - 13.6) / 0.4))
    text(d, (W * 0.32, H / 2 - 40), "KICPA", 150, (255, 255, 255, a))
    text(d, (W * 0.32, H / 2 + 100), "Assistant", 110, (255, 255, 255, a), "Bold")
    return base


APP_BEATS = [
    # (start beat, phone, lines revealed on successive beats)
    (D_APP, "home", ["고르고,", "묻고,", "답을 받는다."]),
    (D_APP + 4, "newchat", ["카테고리를 고르면,", "그 기준으로", "답합니다."]),
    (D_APP + 8, "sidebar", ["대화는", "이 기기에만", "저장됩니다."]),
]


def scene_app(b):
    base = Image.new("RGBA", (W, H), (10, 12, 18, 255))
    idx = min(int((b - D_APP) // 4), 2)
    start, name, lines = APP_BEATS[idx]
    rel = b - start
    # soft brand glow behind the phone
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * 0.52, H * 0.05, W * 0.98, H * 0.95), fill=BLUE + (110,))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
    # phone whips in from the right on the section's downbeat
    p = ease_out(rel / 0.5)
    x = W * 0.72 + (1 - p) * 900
    paste_scaled(base, PHONES[name], (x, H / 2 + 10), 1.0 * punch(rel * BEAT, 0.03, 0.1))
    d = ImageDraw.Draw(base, "RGBA")
    for j, line in enumerate(lines):
        if rel >= j:
            dt = (rel - j) * BEAT
            a = int(255 * ease_out(dt / 0.08))
            y = H / 2 - 150 + j * 150
            text(d, (150, y), line, 118 * punch(dt, 0.06, 0.05), (255, 255, 255, a), anchor="lm")
    return base


def scene_pivot(b):
    base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(base, "RGBA")
    rel = b - E_PIVOT
    line, r0 = ("당신은 회계사입니다.", 0) if rel < 4 else ("검색하는 사람이 아니라.", 4)
    dt = (rel - r0) * BEAT
    a = int(255 * ease_out(dt / 0.35))
    size = 120 + 8 * dt  # slow, confident push instead of a slam
    text(d, (W / 2, H / 2), line, size, (255, 255, 255, a), "Bold")
    return base


def scene_end(b, t):
    base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    rel = b - F_END
    dt = rel * BEAT
    d = ImageDraw.Draw(base, "RGBA")
    if dt < 0.06:
        base.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - dt / 0.06)))))
    move = ease_out((rel - 3.5) / 1.0)
    y1 = H / 2 - 80 - move * 170
    s = punch(dt, 0.08, 0.08)
    text(d, (W / 2, y1), BRAND_LINE[0], 120 * s, WHITE, "Bold")
    text(d, (W / 2, y1 + 150), BRAND_LINE[1], 120 * s, WHITE, "Black")
    if rel >= 3.5:
        p = ease_out((rel - 3.5) / 0.6)
        logo_y = H * 0.72 + (1 - p) * 40
        a = int(255 * p)
        size = 110
        gx = W / 2 - 250
        d.rounded_rectangle((gx - size / 2, logo_y - size / 2, gx + size / 2, logo_y + size / 2), 28, fill=BLUE + (a,))
        text(d, (gx, logo_y + 2), "K", 70, (255, 255, 255, a))
        text(d, (gx + size / 2 + 30, logo_y), "KICPA Assistant", 76, (255, 255, 255, a), "ExtraBold", "lm")
    # fade out
    fade = max(0.0, (t - (DURATION - 0.5)) / 0.5)
    if fade > 0:
        base.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * min(1, fade)))))
    return base


def frame(t):
    b = beat_of(t)
    if t < HOOK:
        return scene_hook(t)
    if b < B_BUILD:
        return scene_open(b)
    if b < STOP:
        return scene_build(b, t)
    if b < C_DROP:
        return Image.new("RGBA", (W, H), (0, 0, 0, 255))
    if b < D_APP:
        return scene_drop(b)
    if b < E_PIVOT:
        return scene_app(b)
    if b < F_END:
        return scene_pivot(b)
    return scene_end(b, t)


def main():
    nframes = int(DURATION * FPS)
    if len(sys.argv) > 1:  # preview stills: python render.py 0.5 3.2 ...
        for s in sys.argv[1:]:
            frame(float(s)).convert("RGB").save(f"build/still_{s}.png")
        return
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", "build/soundtrack.wav", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
           "build/kicpa_assistant_promo.mp4"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(nframes):
        p.stdin.write(frame(i / FPS).convert("RGB").tobytes())
        if i % 150 == 0:
            print(f"{i}/{nframes}", flush=True)
    p.stdin.close()
    p.wait()
    print("wrote build/kicpa_assistant_promo.mp4")


if __name__ == "__main__":
    main()
