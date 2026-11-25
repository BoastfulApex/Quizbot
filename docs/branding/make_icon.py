"""Savolgo brend grafikasi.

Yaratadi:
- docs/branding/savolgo_avatar.png       — 640x640, Telegram bot avatari (/setuserpic)
- docs/branding/savolgo_description.png  — 640x360, bot tavsifi rasmi (/setdescriptionpic)
- bot/assets/welcome.png                 — 1280x720, /start da yuboriladigan rasm

Ishga tushirish:  python docs/branding/make_icon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BRANDING = Path(__file__).resolve().parent

FONT_BLACK = "C:/Windows/Fonts/seguibl.ttf"
FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_REGULAR = "C:/Windows/Fonts/segoeui.ttf"
FONT_EMOJI = "C:/Windows/Fonts/seguiemj.ttf"

INDIGO = (79, 70, 229)
VIOLET = (168, 85, 247)
GREEN = (16, 185, 129)
WHITE = (255, 255, 255)
SCALE = 3  # katta chizib, keyin kichraytiramiz — chiziqlar silliq chiqadi


def _lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def gradient(w: int, h: int) -> Image.Image:
    """Diagonal indigo → binafsha fon (admin panel ranglari bilan bir xil)."""
    small = Image.new("RGB", (64, 64))
    px = small.load()
    for y in range(64):
        for x in range(64):
            px[x, y] = _lerp(INDIGO, VIOLET, (x + y) / 126)
    return small.resize((w, h), Image.BICUBIC).convert("RGBA")


def mark(size: int) -> Image.Image:
    """Shaffof fonda belgi: savol pufagi + '?' + yashil '✓'. size x size RGBA."""
    s = size
    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    bubble = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(bubble)
    bx0, by0, bx1, by1 = int(s * .20), int(s * .19), int(s * .80), int(s * .70)
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=int(s * .12), fill=WHITE)
    d.polygon([(int(s * .33), by1 - 2), (int(s * .48), by1 - 2), (int(s * .30), int(s * .83))], fill=WHITE)

    shadow = bubble.split()[3].filter(ImageFilter.GaussianBlur(s * .02))
    shadow_layer = Image.new("RGBA", (s, s), (30, 20, 90, 0))
    shadow_layer.putalpha(shadow.point(lambda a: int(a * 0.35)))
    layer.alpha_composite(shadow_layer, (0, int(s * .015)))
    layer.alpha_composite(bubble)

    d = ImageDraw.Draw(layer)
    font = ImageFont.truetype(FONT_BLACK, int(s * .40))
    cx, cy = (bx0 + bx1) // 2, (by0 + by1) // 2
    d.text((cx - int(s * .06), cy), "?", font=font, fill=INDIGO, anchor="mm")

    r = int(s * .11)
    ccx, ccy = int(s * .66), int(s * .58)
    ring = max(2, int(s * .022))
    d.ellipse((ccx - r - ring, ccy - r - ring, ccx + r + ring, ccy + r + ring), fill=WHITE)
    d.ellipse((ccx - r, ccy - r, ccx + r, ccy + r), fill=GREEN)
    w = max(2, int(s * .028))
    pts = [(ccx - r * .45, ccy + r * .02), (ccx - r * .1, ccy + r * .38), (ccx + r * .48, ccy - r * .35)]
    d.line(pts, fill=WHITE, width=w, joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=WHITE)
    return layer


def _glow(img: Image.Image, center: tuple[int, int], radius: int, alpha: int) -> None:
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        fill=(255, 255, 255, alpha),
    )
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius * .6)))


def _chip(d: ImageDraw.ImageDraw, img: Image.Image, xy: tuple[int, int], emoji: str, text: str, h: int) -> int:
    """Yarim shaffof 'chip' chizadi, keyingi chip uchun x ni qaytaradi."""
    x, y = xy
    font = ImageFont.truetype(FONT_BOLD, int(h * .42))
    emoji_font = ImageFont.truetype(FONT_EMOJI, int(h * .42))
    pad, gap = int(h * .42), int(h * .18)
    ew = d.textlength(emoji, font=emoji_font)
    tw = d.textlength(text, font=font)
    w = int(pad * 2 + ew + gap + tw)

    chip = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(chip).rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=(255, 255, 255, 46))
    img.alpha_composite(chip)
    d.text((x + pad, y + h / 2), emoji, font=emoji_font, embedded_color=True, anchor="lm")
    d.text((x + pad + ew + gap, y + h / 2), text, font=font, fill=WHITE, anchor="lm")
    return x + w


def avatar(out: Path, size: int = 640) -> None:
    s = size * SCALE
    img = gradient(s, s)
    img.alpha_composite(mark(s))
    img.resize((size, size), Image.LANCZOS).convert("RGB").save(out, optimize=True)


def banner(out: Path, width: int, height: int, *, chips: bool) -> None:
    W, H = width * SCALE, height * SCALE
    img = gradient(W, H)
    _glow(img, (int(W * .22), int(H * .50)), int(H * .42), 70)
    _glow(img, (int(W * .95), int(H * .05)), int(H * .35), 40)

    m = int(H * .78)
    img.alpha_composite(mark(m), (int(W * .22) - m // 2, int(H * .50) - m // 2))

    d = ImageDraw.Draw(img)
    left = int(W * .43)
    title_font = ImageFont.truetype(FONT_BLACK, int(H * .19))
    sub_font = ImageFont.truetype(FONT_BOLD, int(H * .062))

    title_y = int(H * (.34 if chips else .40))
    d.text((left, title_y), "Savolgo", font=title_font, fill=WHITE, anchor="ls")
    d.text((left + 4, title_y + int(H * .10)), "Test yarat. Bellash. O'rgan.", font=sub_font,
           fill=(233, 230, 255), anchor="ls")

    if chips:
        chip_h = int(H * .085)
        row1, row2 = int(H * .56), int(H * .56) + chip_h + int(H * .035)
        gap = int(H * .025)
        x = _chip(d, img, (left, row1), "📝", "Test yaratish", chip_h)
        _chip(d, img, (x + gap, row1), "🤖", "AI savollar", chip_h)
        x = _chip(d, img, (left, row2), "📥", "Word, Excel, PDF", chip_h)
        _chip(d, img, (x + gap, row2), "👥", "Guruhda bellashuv", chip_h)

    img.resize((width, height), Image.LANCZOS).convert("RGB").save(out, optimize=True)


if __name__ == "__main__":
    targets = [
        (BRANDING / "savolgo_avatar.png", lambda p: avatar(p)),
        (BRANDING / "savolgo_description.png", lambda p: banner(p, 640, 360, chips=False)),
        (ROOT / "bot" / "assets" / "welcome.png", lambda p: banner(p, 1280, 720, chips=True)),
    ]
    for path, build in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        build(path)
        print(path)
