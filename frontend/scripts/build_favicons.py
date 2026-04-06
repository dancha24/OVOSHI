# -*- coding: utf-8 -*-
"""Генерация favicon и logo в public/ из корневого «Лого без фона.png»."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "Лого без фона.png"
OUT = Path(__file__).resolve().parents[1] / "public"


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"Нет файла: {SRC}")

    OUT.mkdir(parents=True, exist_ok=True)
    img = Image.open(SRC).convert("RGBA")

    w, h = img.size
    if w != h:
        side = max(w, h)
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        square.paste(img, ((side - w) // 2, (side - h) // 2))
        img = square

    max_side = max(img.size)
    if max_side > 512:
        r = 512 / max_side
        logo_img = img.resize(
            (int(img.width * r), int(img.height * r)), Image.Resampling.LANCZOS
        )
    else:
        logo_img = img
    logo_img.save(OUT / "logo.png", optimize=True)

    img.resize((16, 16), Image.Resampling.LANCZOS).save(
        OUT / "favicon-16x16.png", optimize=True
    )
    img.resize((32, 32), Image.Resampling.LANCZOS).save(
        OUT / "favicon-32x32.png", optimize=True
    )
    img.resize((180, 180), Image.Resampling.LANCZOS).save(
        OUT / "apple-touch-icon.png", optimize=True
    )
    img.resize((192, 192), Image.Resampling.LANCZOS).save(
        OUT / "android-chrome-192x192.png", optimize=True
    )
    img.resize((512, 512), Image.Resampling.LANCZOS).save(
        OUT / "android-chrome-512x512.png", optimize=True
    )

    sizes = [(16, 16), (32, 32), (48, 48)]
    icons = [img.resize(s, Image.Resampling.LANCZOS) for s in sizes]
    icons[-1].save(
        OUT / "favicon.ico",
        format="ICO",
        sizes=[(i.width, i.height) for i in icons],
        append_images=icons[:-1],
    )

    print("OK:", OUT)


if __name__ == "__main__":
    main()
