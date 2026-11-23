# -*- coding: utf-8 -*-
"""Численная верификация: припуски везде ненулевые, юбка — честное кольцо-сектор."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.models import MODELS
from core.geom import dist, pt_sub, pt_len, polygon_area


def min_edge_gap(piece, seg_idx):
    """Минимальный зазор шов-крой по ВНУТРЕННИМ точкам сегмента.
    Концы, лежащие на сгибах (припуск 0), исключены: для отрезка берём
    середину, для кривых — средние 50% точек."""
    g = piece.contour.seg_groups(48)
    seg = g[seg_idx]
    cut = piece.cut_poly
    n = len(seg)
    if n <= 2:
        pts = [seg[0], seg[1]] if n == 2 else [seg[0]]
        pts = [((pts[0][0] + pts[-1][0]) / 2.0, (pts[0][1] + pts[-1][1]) / 2.0)]
    else:
        lo, hi = int(n * 0.25), int(n * 0.75) + 1
        pts = seg[lo:hi]
    worst = 1e9
    for p in pts:
        d = min(dist(p, q) for q in cut)
        worst = min(worst, d)
    return worst


def verify_allowances():
    print("=== Припуски: минимальный зазор шов-крой по сегментам ===")
    bad = 0
    for model in MODELS:
        d = model.build(model.default_measurements(), model.default_params())
        for piece in d.pieces:
            edges = piece.allowance_edges or []
            row = []
            for i, a in enumerate(edges):
                if a <= 1e-9:
                    continue  # сгиб — припуск не нужен
                gap = min_edge_gap(piece, i)
                row.append("%d:%.2f" % (i, gap))
                if gap < a * 0.55:
                    print("  !! %s/%s сегм.%d: припуск %g, зазор %.2f — МАЛО"
                          % (model.model_id, piece.piece_id, i, a, gap))
                    bad += 1
        print("  %-12s %s" % (model.model_id, " ".join(
            "%s/%s %s" % (p.piece_id, p.name.split()[0], " ".join(
                s for s in [])) or p.piece_id for p in d.pieces)))
    print("  проблемных сегментов:", bad)


def verify_skirt():
    print()
    print("=== Юбка-солнце: геометрия сектора ===")
    m = MODELS[5]
    assert m.model_id == "skirt_sun"
    d = m.build(m.default_measurements(), m.default_params())
    p = d.pieces[0]
    r = [v for n, v in d.checks if n.startswith("Радиус линии пояса")][0]
    R = [v for n, v in d.checks if n.startswith("Радиус линии низа")][0]
    g = p.contour.seg_groups(64)
    # сегмент 0 — дуга пояса: все точки на расстоянии r от начала координат
    err_r = max(abs(pt_len(q) - r) for q in g[0])
    # сегмент 2 — дуга низа: все точки на расстоянии R
    err_R = max(abs(pt_len(q) - R) for q in g[2])
    # сегменты 1 и 3 — прямые радиальные: точки на осях
    seg1_axis = all(abs(q[1]) < 1e-6 for q in g[1])
    seg3_axis = all(abs(q[0]) < 1e-6 for q in g[3])
    # угол сектора: угол между концами дуги
    a0 = math.atan2(g[0][0][1], g[0][0][0])
    a1 = math.atan2(g[0][-1][1], g[0][-1][0])
    angle = math.degrees(abs(a1 - a0))
    print("  дуга пояса: макс. отклонение от r=%.2f: %.3f см" % (r, err_r))
    print("  дуга низа:  макс. отклонение от R=%.2f: %.3f см" % (R, err_R))
    print("  боковой срез горизонтален (y=0): %s" % seg1_axis)
    print("  сгиб вертикален (x=0): %s" % seg3_axis)
    print("  угол сектора: %.1f град (нужно 90)" % angle)
    # сборка: перед (сектор) + зад (сектор), каждый на сгибе -> полный круг
    waist_arc = sum(dist(g[0][j], g[0][j + 1]) for j in range(len(g[0]) - 1))
    print("  дуга пояса сектора: %.1f см; полный круг 2*pi*r = %.1f; 4 сектора = %.1f"
          % (waist_arc, 2 * math.pi * r, 4 * waist_arc))
    ok = (err_r < 0.05 and err_R < 0.05 and seg1_axis and seg3_axis
          and abs(angle - 90) < 0.5)
    print("  ВЕРДИКТ:", "СЕКТОР КОРРЕКТЕН" if ok else "ОШИБКА ГЕОМЕТРИИ")
    # площадь сектора кольца против площадей по формуле
    area = abs(polygon_area(p.contour.points(64)))
    formula = math.pi * (R * R - r * r) / 4.0
    print("  площадь детали %.1f см2, формула pi*(R^2-r^2)/4 = %.1f см2 (расхожд. %.1f%%)"
          % (area, formula, abs(area - formula) / formula * 100))


if __name__ == "__main__":
    verify_allowances()
    verify_skirt()
