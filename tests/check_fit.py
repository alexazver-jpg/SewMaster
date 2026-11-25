# -*- coding: utf-8 -*-
"""Численная проверка посадки всех моделей: отверстия для ног, пояс, горловина."""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.models import MODELS_BY_ID
from core.geom import dist


def seglen(piece, idx):
    g = piece.contour.seg_groups(48)
    seg = g[idx]
    return sum(dist(seg[j], seg[j + 1]) for j in range(len(seg) - 1))


def panel_opening(draft, seg_idx):
    """Сумма срезов обеих панелей x 2 (детали кроятся на сгибе)."""
    total = 0.0
    for p in draft.pieces:
        g = p.contour.seg_groups(48)
        if len(g) > seg_idx:
            seg = g[seg_idx]
            total += sum(dist(seg[j], seg[j + 1]) for j in range(len(seg) - 1))
    return 2.0 * total


def check(mid):
    m = MODELS_BY_ID[mid]
    meas = m.default_measurements()
    d = m.build(meas, m.default_params())
    print("=== %s (%s)" % (mid, m.title))
    hips = meas.get("hips", 0)
    thigh = meas.get("thigh") or (hips * 0.62 if hips else 0)
    if mid in ("boxers", "shorts"):
        hem = seglen(d.pieces[0], 2)
        opening = 2.0 * hem  # обе панели одинаковы по низу
        waist = panel_opening(d, 0)
        print("  отверстие ноги: %.1f (бедро %.1f) %s"
              % (opening, thigh, "OK" if opening >= thigh + 1 else "МАЛО!"))
        print("  пояс изделия: %.1f (бёдра %.1f) %s"
              % (waist, hips, "OK" if waist >= hips + 1 else "МАЛО!"))
    if mid == "briefs":
        waist = panel_opening(d, 0)
        side_f = seglen(d.pieces[0], 1)
        side_b = seglen(d.pieces[1], 1)
        print("  пояс изделия: %.1f (бёдра %.1f) %s"
              % (waist, hips, "OK" if waist >= hips + 1 else "МАЛО!"))
        print("  боковые швы: перед %.2f / зад %.2f %s"
              % (side_f, side_b, "OK" if abs(side_f - side_b) < 0.3 else "НЕ РАВНЫ!"))
    if mid in ("tank", "tee", "longsleeve"):
        neck_open = seglen(d.pieces[0], 0) + seglen(d.pieces[1], 0)
        neck = meas.get("neck", 0)
        need = neck * 0.55
        print("  горловина: %.1f (нужно >= %.1f для Ош %g) %s"
              % (neck_open, need, neck, "OK" if neck_open >= need else "МАЛО!"))
        side_f = seglen(d.pieces[0], 3)
        side_b = seglen(d.pieces[1], 3)
        print("  боковые швы: перед %.2f / зад %.2f %s"
              % (side_f, side_b, "OK" if abs(side_f - side_b) < 0.3 else "НЕ РАВНЫ!"))
    if mid == "skirt_sun":
        r = 0.0
        for name, v in d.checks:
            if name.startswith("Радиус линии пояса"):
                r = v
        waist_open = 2 * math.pi * r
        print("  обхват пояса: %.1f (бёдра %.1f) %s"
              % (waist_open, hips, "OK" if waist_open >= hips + 1.5 else "МАЛО!"))
        hem_arc = [v for n, v in d.checks if "Дуга низа" in n][0]
        print("  дуга низа полотнища: %.1f см" % hem_arc)
    if mid == "longsleeve":
        hem = seglen(d.pieces[2], 2)
        wrist = meas.get("wrist") or meas["arm"] * 0.53
        print("  низ рукава: %.1f (запястье %.1f) %s"
              % (hem, wrist, "OK" if hem >= wrist + 3 else "УЗКО!"))
    if mid == "pillowcase":
        val = lambda pref: [v for n, v in d.checks if n.startswith(pref)][0]
        w_cut = val("Ширина полотнища в крое")
        l_cut = val("Длина полотнища в крое")
        a_top = val("Верхняя линия сгиба")
        b_bot = val("Нижняя линия сгиба")
        pw, pl = meas["pillow_w"], meas["pillow_l"]
        fin_l = l_cut - a_top - b_bot
        fin_w = w_cut - 2.0 * m.default_params()["allowance"]
        print("  крой: %.1f x %.1f (подушка %g x %g)"
              % (w_cut, l_cut, pw, pl))
        print("  готовый размер: %.1f x %.1f %s"
              % (fin_w, fin_l,
                 "OK" if abs(fin_w - pw) < 0.05 and abs(fin_l - pl) < 0.05
                 else "НЕ СХОДИТСЯ!"))
        print("  линии сгиба: верх %.1f / низ %.1f от краёв"
              % (a_top, b_bot))


if __name__ == "__main__":
    for mid in ("briefs", "boxers", "tank", "tee", "longsleeve",
                "skirt_sun", "shorts", "pillowcase"):
        check(mid)
