#!/usr/bin/env python3
"""Regenerate the two images of the repository.

    assets/icon.png            512 x 512    plugin and marketplace icon
    assets/social-preview.png  1280 x 640   GitHub social preview (upload it in the repository settings)

    python assets/make_assets.py

This is the only script of the project that needs a package outside the standard library:
Pillow (pip install pillow). Nothing else imports it and no test depends on it. The images
use the Inter and DejaVu Sans Mono typefaces when they are installed and fall back to
Pillow's built-in font otherwise, so regenerated images can differ from the committed ones.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SCALE = 2  # draw large, shrink once: smooth edges

INK = (15, 16, 20)          # background
PAPER = (236, 233, 226)     # main text
MUTED = (139, 143, 155)     # secondary text
LINE = (52, 55, 66)         # ring
ACCENT = (255, 78, 44)      # the step that proves

STEPS = ["FRAME", "SCOPE", "GROUND", "PLAN", "BUILD", "PROVE", "DELIVER"]
PROVE = STEPS.index("PROVE")

FONT_DIRS = [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts",
             Path("/Library/Fonts"), Path("/System/Library/Fonts"), Path("C:/Windows/Fonts")]


def find_font(names: Sequence[str]) -> Optional[Path]:
    for name in names:
        for folder in FONT_DIRS:
            if folder.is_dir():
                found = next(folder.rglob(name), None)
                if found:
                    return found
    return None


def font(names: Sequence[str], size: int) -> ImageFont.ImageFont:
    path = find_font(names)
    if path:
        return ImageFont.truetype(str(path), size * SCALE)
    return ImageFont.load_default(size * SCALE)


def display(size: int) -> ImageFont.ImageFont:
    return font(["InterDisplay-Black.otf", "Inter-Black.otf", "DejaVuSans-Bold.ttf"], size)


def sans(size: int, weight: str = "Medium") -> ImageFont.ImageFont:
    return font([f"Inter-{weight}.otf", "DejaVuSans.ttf"], size)


def mono(size: int, bold: bool = False) -> ImageFont.ImageFont:
    return font(["DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf", "DejaVuSansMono.ttf"], size)


def px(value: float) -> int:
    return int(round(value * SCALE))


def spaced(draw: ImageDraw.ImageDraw, xy: Tuple[float, float], text: str, face: ImageFont.ImageFont,
           fill: Tuple[int, int, int], tracking: float = 0.0) -> float:
    """Draw text with extra letter spacing. Returns the x position after the last letter (unscaled)."""
    x, y = px(xy[0]), px(xy[1])
    for letter in text:
        draw.text((x, y), letter, font=face, fill=fill)
        x += draw.textlength(letter, font=face) + px(tracking)
    return x / SCALE


def ring(draw: ImageDraw.ImageDraw, centre: Tuple[float, float], radius: float, dot: float, monogram_size: int) -> None:
    """Seven steps on an open ring; the sixth, PROVE, is the one in colour."""
    cx, cy = centre
    gap = 46.0                                   # degrees left open at the top: the loop has a start and an end
    start, sweep = -90 + gap / 2, 360 - gap
    box = [px(cx - radius), px(cy - radius), px(cx + radius), px(cy + radius)]
    draw.arc(box, start, start + sweep, fill=LINE, width=px(max(2.0, radius / 42)))
    # the part of the path already walked when the work reaches PROVE
    draw.arc(box, start, start + sweep * PROVE / (len(STEPS) - 1), fill=MUTED, width=px(max(2.0, radius / 42)))
    for index in range(len(STEPS)):
        angle = math.radians(start + sweep * index / (len(STEPS) - 1))
        x, y = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
        size = dot * (1.75 if index == PROVE else 1.0)
        colour = ACCENT if index == PROVE else (PAPER if index < PROVE else MUTED)
        halo = size + dot * 0.9
        draw.ellipse([px(x - halo), px(y - halo), px(x + halo), px(y + halo)], fill=INK)
        draw.ellipse([px(x - size), px(y - size), px(x + size), px(y + size)], fill=colour)
    face = display(monogram_size)
    left, top, right, bottom = draw.textbbox((0, 0), "DM", font=face)
    draw.text((px(cx) - (left + right) / 2, px(cy) - (top + bottom) / 2), "DM", font=face, fill=PAPER)


def finish(image: Image.Image, size: Tuple[int, int], target: Path) -> None:
    image.resize(size, Image.LANCZOS).save(target, optimize=True)
    print(f"{target.relative_to(HERE.parent).as_posix()}: {size[0]} x {size[1]}, {target.stat().st_size / 1024:.0f} KB")


def icon() -> None:
    size = 512
    image = Image.new("RGB", (px(size), px(size)), INK)
    ring(ImageDraw.Draw(image), (size / 2, size / 2), radius=186, dot=13, monogram_size=150)
    finish(image, (size, size), HERE / "icon.png")


def social_preview() -> None:
    width, height = 1280, 640
    image = Image.new("RGB", (px(width), px(height)), INK)
    draw = ImageDraw.Draw(image)
    left = 84

    spaced(draw, (left, 92), "AGENT SKILL  ·  PROMPT FRAMEWORK  ·  BENCHMARK", mono(19, bold=True), ACCENT, tracking=2.4)

    title = display(104)
    draw.text((px(left - 5), px(128)), "DIAVLO MIND", font=title, fill=PAPER)
    title_end = (px(left - 5) + draw.textlength("DIAVLO MIND", font=title)) / SCALE
    draw.text((px(title_end + 22), px(197)), "Fable Edition", font=sans(30, "Regular"), fill=MUTED)

    lines: List[str] = ["Planning, verification and multi-agent roles", "for Claude Code, Codex, Gemini CLI and any LLM."]
    for index, line in enumerate(lines):
        draw.text((px(left), px(282 + index * 48)), line, font=sans(35, "Medium"), fill=PAPER)

    # the loop, with the proving step in colour
    x, y, face = float(left), 424.0, mono(21, bold=True)
    for index, step in enumerate(STEPS):
        x = spaced(draw, (x, y), step, face, ACCENT if index == PROVE else PAPER, tracking=0.6)
        if index < len(STEPS) - 1:
            x = spaced(draw, (x + 9, y), "→", face, MUTED) + 9

    draw.text((px(left), px(516)), "10 rules  ·  20 procedures  ·  8 role agents  ·  4 modes  ·  8 benchmark tasks",
              font=mono(19), fill=MUTED)

    ring(draw, (1098, 326), radius=120, dot=9, monogram_size=92)
    finish(image, (width, height), HERE / "social-preview.png")


def main() -> int:
    icon()
    social_preview()
    return 0


if __name__ == "__main__":
    sys.exit(main())
