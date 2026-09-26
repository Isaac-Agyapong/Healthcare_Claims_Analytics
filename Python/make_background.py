"""Generate the dark dashboard background: deep-navy gradient, soft glowing colour blooms and a faint
network-of-nodes pattern ("connected health data"). Tiles sit on top, so it only shows in the gaps.
Output: dashboard/assets/page_background.png (1280x720, drawn at 2x for sharpness)."""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "assets" / "page_background.png"
S = 2
W, H = 1280 * S, 720 * S
TOP, BOTTOM = (10, 18, 36), (16, 28, 54)          # deep navy gradient (page colour #0B1426)


def main():
    random.seed(7)
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        row = tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM))
        for x in range(W):
            px[x, y] = row
    img = img.convert("RGBA")

    # glowing blooms: cyan top-right, rose bottom-left, violet centre
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse([880 * S, -260 * S, 1560 * S, 360 * S], fill=(56, 189, 248, 70))
    g.ellipse([-320 * S, 380 * S, 420 * S, 1020 * S], fill=(251, 113, 133, 55))
    g.ellipse([420 * S, 180 * S, 900 * S, 620 * S], fill=(129, 140, 248, 28))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(140 * S)))

    # faint network of nodes and links
    net = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(net)
    nodes = [(random.randint(0, W), random.randint(0, H)) for _ in range(70)]
    for i, (x1, y1) in enumerate(nodes):
        for x2, y2 in nodes[i + 1:]:
            dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            if dist < 190 * S:
                d.line([(x1, y1), (x2, y2)], fill=(148, 190, 255, int(34 * (1 - dist / (190 * S)))), width=S)
    for x, y in nodes:
        r = random.choice([2, 3, 4]) * S
        d.ellipse([x - r, y - r, x + r, y + r], fill=(160, 205, 255, 60))
    img = Image.alpha_composite(img, net.filter(ImageFilter.GaussianBlur(0.5 * S)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
