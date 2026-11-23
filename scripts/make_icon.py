# -*- coding: utf-8 -*-
"""Генерация иконки SewMaster (запускается один раз при подготовке релиза).

Рисует «узор выкройки»: игла с ниткой и пунктирную линию шва на синем фоне.
Не входит в runtime-зависимости приложения.
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")
os.makedirs(OUT_DIR, exist_ok=True)

BLUE = (29, 78, 216)
BLUE_DARK = (30, 58, 138)
WHITE = (255, 255, 255)
RED = (220, 38, 38)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size * 0.18
    # скруглённый квадрат — фон
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BLUE)
    # лёгкий блик в левом верхнем углу
    d.pieslice([0, 0, size, size], 180, 270, fill=(59, 108, 232, 255))

    s = size / 256.0
    # «лист выкройки» — белый скруглённый прямоугольник под углом
    sheet = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sheet)
    ds.rounded_rectangle([52 * s, 44 * s, 204 * s, 232 * s],
                         radius=14 * s, fill=WHITE)
    sheet = sheet.rotate(-8, resample=Image.BICUBIC, center=(size / 2, size / 2))
    img.alpha_composite(sheet)
    d = ImageDraw.Draw(img)

    # пунктирная «линия шва» на листе (красная) — плавная кривая
    pts = []
    for i in range(25):
        t = i / 24.0
        x = (70 + 118 * t) * s
        y = (196 - 90 * math.sin(t * math.pi * 0.85)) * s
        pts.append((x, y))
    # рисуем пунктир отрезками
    for i in range(0, len(pts) - 1, 2):
        if i + 1 < len(pts):
            d.line([pts[i], pts[i + 1]], fill=RED, width=int(6 * s))

    # сплошная линия кроя (тёмная) параллельно ниже
    pts2 = [(x + 16 * s, y + 16 * s) for (x, y) in pts]
    for i in range(len(pts2) - 1):
        d.line([pts2[i], pts2[i + 1]], fill=(17, 24, 39), width=int(5 * s))

    # ножницы-точка: маленький круг на конце линии
    cx, cy = pts[-1]
    d.ellipse([cx - 9 * s, cy - 9 * s, cx + 9 * s, cy + 9 * s],
              fill=BLUE_DARK, outline=WHITE, width=int(3 * s))
    return img


def main():
    base = draw_icon(256)
    base.save(os.path.join(OUT_DIR, "icon.png"))
    base.save(os.path.join(OUT_DIR, "icon.ico"),
              sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128),
                     (256, 256)])
    print("иконки созданы:", os.listdir(OUT_DIR))


if __name__ == "__main__":
    main()
