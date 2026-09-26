"""Generate the dashboard page background: a cool slate gradient with a faint diagonal grid and a soft
blue glow in the lower-left corner. Low contrast so it frames the report without competing with it.
Output: dashboard/assets/page_background.png (1280x720, drawn at 2x for sharpness)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "assets" / "page_background.png"
S = 2
W, H = 1280 * S, 720 * S
TOP, BOTTOM = (240, 243, 247), (226, 232, 240)     # slate gradient (matches the page colour #EDF1F5)


def main():
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        row = tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM))
        for x in range(W):
            px[x, y] = row

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    # faint diagonal grid (both directions) below the top bar
    step = 36 * S
    for k in range(-H, W + H, step):
        d.line([(k, 70 * S), (k + H, H + 70 * S)], fill=(47, 109, 181, 18), width=S)
        d.line([(k, H), (k + H, 70 * S - H + H)], fill=(47, 109, 181, 12), width=S)
    # soft glow, lower-left
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([-260 * S, 420 * S, 520 * S, 1040 * S], fill=(74, 144, 217, 40))
    overlay = Image.alpha_composite(overlay, glow.filter(ImageFilter.GaussianBlur(120 * S)))

    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
