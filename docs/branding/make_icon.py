"""Bot avatarini yaratadi: docs/branding/savolgo_avatar.png (640x640, Telegram uchun)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 640
SCALE = 4  # silliq chiziqlar uchun katta chizib, keyin kichraytiramiz
S = SIZE * SCALE
OUT = Path(__file__).with_name("savolgo_avatar.png")
FONT = "C:/Windows/Fonts/seguibl.ttf"


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


# Fon: diagonal indigo → binafsha gradient (admin panel ranglari bilan bir xil)
top, bottom = (79, 70, 229), (168, 85, 247)
bg = Image.new("RGB", (S, S))
px = bg.load()
for y in range(S):
    for x in range(0, S, 4):
        c = lerp(top, bottom, (x + y) / (2 * S))
        for dx in range(4):
            px[x + dx, y] = c

img = bg.convert("RGBA")

# Savol pufagi (speech bubble) — oq, markazda, Telegram doira kesimiga sig'adi
bubble = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(bubble)
bx0, by0, bx1, by1 = int(S * .20), int(S * .19), int(S * .80), int(S * .70)
d.rounded_rectangle((bx0, by0, bx1, by1), radius=int(S * .12), fill=(255, 255, 255, 255))
d.polygon([(int(S * .33), by1 - 10), (int(S * .48), by1 - 10), (int(S * .30), int(S * .83))],
          fill=(255, 255, 255, 255))

shadow = bubble.split()[3].filter(ImageFilter.GaussianBlur(S * .02))
shadow_layer = Image.new("RGBA", (S, S), (30, 20, 90, 0))
shadow_layer.putalpha(shadow.point(lambda a: a * 0.35))
img.alpha_composite(shadow_layer, (0, int(S * .015)))
img.alpha_composite(bubble)

# "?" belgisi pufak ichida, gradient rangida
d = ImageDraw.Draw(img)
font = ImageFont.truetype(FONT, int(S * .40))
cx, cy = (bx0 + bx1) // 2, (by0 + by1) // 2
d.text((cx - int(S * .06), cy), "?", font=font, fill=(79, 70, 229), anchor="mm")

# To'g'ri javob belgisi — yashil doira ichida oq "✓"
r = int(S * .11)
ccx, ccy = int(S * .66), int(S * .58)
d.ellipse((ccx - r - 14, ccy - r - 14, ccx + r + 14, ccy + r + 14), fill=(255, 255, 255))
d.ellipse((ccx - r, ccy - r, ccx + r, ccy + r), fill=(16, 185, 129))
w = int(S * .028)
d.line([(ccx - r * .45, ccy + r * .02), (ccx - r * .1, ccy + r * .38), (ccx + r * .48, ccy - r * .35)],
       fill=(255, 255, 255), width=w, joint="curve")
for x, y in [(ccx - r * .45, ccy + r * .02), (ccx + r * .48, ccy - r * .35)]:
    d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=(255, 255, 255))

img.resize((SIZE, SIZE), Image.LANCZOS).convert("RGB").save(OUT, optimize=True)
print(OUT)
