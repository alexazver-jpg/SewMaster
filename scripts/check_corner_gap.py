# -*- coding: utf-8 -*-
"""Минимальный зазор шов-крой на сегментах С ненулевым припуском.

Сгибы (припуск 0) исключаются — там шов и крой совпадают по конструкции.
Ищем реальные защемления припуска на рабочих швах, включая углы.
"""
import sys
sys.path.insert(0, '.')
from core.models import MODELS_BY_ID
from core.geom import dist


def min_gap_active(piece):
    """Мин. зазор по точкам сегментов с ненулевым припуском.

    Точки на стыке с нулевым (сгиб) сегментом пропускаются — совпадение
    шва и кроя там конструктивно.
    """
    edges = piece.allowance_edges
    if edges is None:
        edges = [piece.allowance] * len(piece.contour.segs)
    n = len(edges)
    cut_pts = piece.cut_poly
    worst = (1e9, None, -1)
    groups = piece.contour.seg_groups(96)
    for i in range(n):
        if edges[i] <= 1e-9:      # сгиб — пропуск
            continue
        prev_a = edges[(i - 1) % n]
        next_a = edges[(i + 1) % n]
        pts = groups[i]
        for j, p in enumerate(pts):
            if j == 0 and prev_a <= 1e-9:
                continue           # стык со сгибом
            if j == len(pts) - 1 and next_a <= 1e-9:
                continue           # стык со сгибом
            d = min(dist(p, q) for q in cut_pts)
            if d < worst[0]:
                worst = (d, p, i)
    return worst


def main():
    for mid in ("shorts", "boxers", "skirt_sun", "briefs", "longsleeve", "tee", "tank"):
        mdef = MODELS_BY_ID[mid]
        res = mdef.build(mdef.default_measurements(), mdef.default_params())
        print("=== %s ===" % mid)
        for pc in res.pieces:
            gap, pt, seg_i = min_gap_active(pc)
            allow = (pc.allowance_edges or [pc.allowance] * len(pc.contour.segs))[seg_i]
            flag = "OK" if gap >= 0.5 * allow - 1e-6 else ("PINCH" if gap > 0.05 else "DEFECT!")
            print("  %-22s мин. зазор %.3f см (припуск %.1f) у (%.1f, %.1f), сегм. %d  %s"
                  % (pc.name, gap, allow, pt[0], pt[1], seg_i, flag))


if __name__ == "__main__":
    main()
