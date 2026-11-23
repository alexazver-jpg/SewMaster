# -*- coding: utf-8 -*-
"""Быстрая визуальная проверка геометрии: PNG-превью всех моделей (для разработки)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

fm.fontManager.addfont('/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf')
plt.rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from core.models import MODELS

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "preview_png")
os.makedirs(OUT, exist_ok=True)


def draw_piece(ax, piece):
    seam = piece.contour.points(24) + [piece.contour.start]
    cut = piece.cut_poly + [piece.cut_poly[0]]
    ax.fill([p[0] for p in cut], [p[1] for p in cut], color="#dbeafe", zorder=1)
    ax.plot([p[0] for p in cut], [p[1] for p in cut], color="#1e3a8a", lw=1.8, zorder=3,
            label="линия кроя (с припуском)")
    ax.plot([p[0] for p in seam], [p[1] for p in seam], color="#dc2626", lw=1.2,
            ls="--", zorder=4, label="линия шва")
    if piece.grain:
        (x1, y1), (x2, y2) = piece.grain
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="<->", color="#166534", lw=1.5))
        ax.text((x1 + x2) / 2 + 0.4, (y1 + y2) / 2, "долевая", fontsize=7,
                color="#166534", rotation=90, va="center")
    for (a, b) in piece.folds:
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#9333ea", lw=1.5, ls="-.")
    for lbl in piece.labels:
        ax.text(lbl.pt[0], lbl.pt[1], "\n".join(lbl.lines), fontsize=8,
                ha="center", va="center", color="#111827", zorder=5,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#9ca3af", alpha=0.85))


def main():
    for model in MODELS:
        meas = model.default_measurements()
        params = model.default_params()
        draft = model.build(meas, params)
        n = len(draft.pieces)
        fig, axes = plt.subplots(1, n, figsize=(5 * n, 6.5), constrained_layout=True)
        if n == 1:
            axes = [axes]
        fig.suptitle("%s — %s" % (model.title, " / ".join(
            "%s: %g" % c for c in draft.checks[:2])), fontsize=11)
        for ax, piece in zip(axes, draft.pieces):
            draw_piece(ax, piece)
            x0, y0, x1, y1 = piece.bbox(True)
            ax.set_title("%s (%s)\n%s · припуск %g см" % (
                piece.name, piece.size_text(), piece.cut_note, piece.allowance),
                fontsize=9)
            ax.set_xlim(x0 - 2, x1 + 2)
            ax.set_ylim(y1 + 2, y0 - 2)  # инверсия: y вниз
            ax.set_aspect("equal")
            ax.grid(True, ls=":", lw=0.5)
        out = os.path.join(OUT, "preview_%s.png" % model.model_id)
        fig.savefig(out, dpi=110)
        plt.close(fig)
        print("OK", model.model_id, "->", os.path.basename(out),
              "| детали:", [p.name for p in draft.pieces],
              "| расход:", draft.fabric)


if __name__ == "__main__":
    main()
