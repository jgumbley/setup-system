#!/usr/bin/env python3
"""Render the committed Moonlight cover set used by HAL's Sunshine role."""

import os
import sys

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 600, 800
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# name -> (title, subtitle, background, accent)
APPS = {
    "eaadwig": ("Eadwig", "OpenMW · Buildwas", "#10261f", "#3fb27f"),
    "tmux": ("Terminal", "tmux · HAL", "#0d1a0d", "#4dcc4d"),
    "morrowind": ("Morrowind", "GOTY · OpenMW", "#241a0a", "#d9a441"),
    "quake3": ("Quake III Arena", "baseq3 · quake3e", "#260f0f", "#cc3329"),
    "rocknix": ("ROCKNIX", "placeholder", "#1a1026", "#8a5fd6"),
}


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def fit_font(draw, value, max_width, start_size):
    size = start_size
    while size > 10:
        font = load_font(FONT_BOLD, size)
        if draw.textlength(value, font=font) <= max_width:
            return font
        size -= 4
    return load_font(FONT_BOLD, 10)


def render(name, spec, output_dir):
    title, subtitle, background, accent = spec
    image = Image.new("RGB", (WIDTH, HEIGHT), background)
    draw = ImageDraw.Draw(image)

    draw.rectangle([0, 0, WIDTH, 24], fill=accent)
    draw.rectangle([0, HEIGHT - 24, WIDTH, HEIGHT], fill=accent)

    title_font = fit_font(draw, title, WIDTH - 80, 96)
    title_width = draw.textlength(title, font=title_font)
    ascent, descent = title_font.getmetrics()
    title_height = ascent + descent
    title_y = int(HEIGHT * 0.45) - title_height // 2
    draw.text(
        ((WIDTH - title_width) / 2, title_y),
        title,
        font=title_font,
        fill="#f2f2f2",
    )

    subtitle_font = load_font(FONT_REGULAR, 34)
    subtitle_width = draw.textlength(subtitle, font=subtitle_font)
    draw.text(
        ((WIDTH - subtitle_width) / 2, title_y + title_height + 24),
        subtitle,
        font=subtitle_font,
        fill=accent,
    )

    output_path = os.path.join(output_dir, f"{name}.png")
    image.save(output_path)
    return output_path


def main():
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "covers"
    os.makedirs(output_dir, exist_ok=True)
    for name, spec in APPS.items():
        print(render(name, spec, output_dir))


if __name__ == "__main__":
    main()
