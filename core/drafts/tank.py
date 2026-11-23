# -*- coding: utf-8 -*-
"""Выкройка: майка-безрукавка («алкоголичка», tank top).

Полочка и спинка кроятся на сгибе по средней линии. Бретели — цельнокроеные
(продолжение полотнища). Горловина и проймы обрабатываются окантовкой
(косая бейка) или подгибкой.

Важно: нижняя точка проймы (U) одинакова у полочки и спинки, поэтому
боковые швы получаются равной длины.

Сегменты контура: 0 — горловина, 1 — бретель, 2 — пройма, 3 — боковой шов,
4 — низ, 5 — средняя линия (СГИБ, припуск 0).
"""
from __future__ import annotations

from typing import Dict

from ..geom import Contour, Pt, dist
from ..piece import (DraftResult, Notch, PatternPiece, PieceLabel, SeamInfo)

FIT_EASE = {"fit": 1.5, "free": 4.0}   # свобода облегания по груди


def build(m: Dict[str, float], p: Dict[str, object]) -> DraftResult:
    chest = float(m["chest"])
    hips = float(m.get("hips") or chest)
    length = float(m["length"])

    fit = str(p.get("fit", "fit"))
    ease = FIT_EASE.get(fit, 1.5)
    strap_w = float(p.get("strap_w", 4.0))
    neck_f = float(p.get("neck_front", 7.5))
    neck_b = 2.5
    allow = float(p.get("allowance", 1.0))

    w = chest / 4.0 + ease / 2.0
    hem_w = max(w, hips / 4.0 + 1.0 + ease / 2.0)
    neck_w = chest / 10.0 + 1.5
    arm_d = chest / 10.0 + 9.0 + (1.0 if fit == "free" else 0.0)

    # общие точки проймы/бокового шва — гарантируют равные боковые швы
    U = (w - 1.2, arm_d)               # нижняя точка проймы (перед и зад)
    H = (hem_w, length)                # низ по боку

    def panel(piece_id: str, name: str, neck_depth: float,
              arm_c2_dx: float, tag: str) -> PatternPiece:
        N0 = (0.0, neck_depth)                 # нижняя точка горловины по центру
        N1 = (neck_w, 1.2)                     # горловина на плечевом крае
        A1 = (neck_w + strap_w, 3.2)           # конец бретели (верх проймы)

        c = Contour(N0)
        c.cubic((neck_w * 0.35, neck_depth * 0.9), (neck_w * 0.8, 0.4), N1)   # горловина
        c.line(A1)                                                            # бретель
        c.cubic((A1[0] + 0.8, A1[1] + 4.2),
                (U[0] - arm_c2_dx, U[1] - 4.0), U)                            # пройма
        c.line(H)                                                             # боковой шов
        c.line((0.0, length))                                                 # низ
        c.line(N0)                                                            # средняя линия (сгиб)

        piece = PatternPiece(piece_id, name, c,
                             "1 деталь со сгибом (сгиб — по средней линии)")
        piece.allowance = allow
        piece.allowance_edges = [allow, allow, allow, allow, allow, 0.0]
        piece.folds = [((0.0, neck_depth + 3.0), (0.0, length - 3.0))]
        piece.grain = ((w * 0.6, arm_d * 0.6), (w * 0.6, length - 4.0))
        piece.notches = [Notch((U[0], arm_d + 5.0), 180.0, "боковой шов")]
        piece.labels = [PieceLabel((w * 0.42, (arm_d + length) / 2.0),
                                   [tag, "сгиб по средней линии"], bold=True)]
        return piece

    p_front = panel("front", "ПОЛОЧКА МАЙКИ", neck_f, 6.0, "ПОЛОЧКА (перед)")
    p_back = panel("back", "СПИНКА МАЙКИ", neck_b, 4.5, "СПИНКА (зад)")

    # контрольные длины
    gf = p_front.contour.seg_groups()
    gb = p_back.contour.seg_groups()

    def glen(g, idx):
        return sum(dist(g[idx][i], g[idx][i + 1]) for i in range(len(g[idx]) - 1))

    side_f = glen(gf, 3)
    side_b = glen(gb, 3)
    armhole_f = glen(gf, 2)
    armhole_b = glen(gb, 2)
    shoulder = dist((neck_w, 1.2), (neck_w + strap_w, 3.2))
    neck_line_f = glen(gf, 0)
    neck_line_b = glen(gb, 0)

    if abs(side_f - side_b) > 0.05:
        raise AssertionError("Боковые швы полочки и спинки должны совпадать: "
                             "%.3f != %.3f" % (side_f, side_b))

    checks = [
        ("Боковой шов (перед = зад)", side_f),
        ("Пройма: полочка", armhole_f),
        ("Пройма: спинка", armhole_b),
        ("Длина бретели (плечевой край)", shoulder),
        ("Горловина: полочка + спинка", neck_line_f + neck_line_b),
    ]

    seams = [
        SeamInfo("shoulder", "Плечевые швы (бретели)", "shoulder", shoulder,
                 "Стачать полочку и спинку по плечевым краям бретелей (2 шва)."),
        SeamInfo("side", "Боковые швы", "side", side_f,
                 "Стачать полочку и спинку по боковым срезам (2 шва)."),
        SeamInfo("neck", "Горловина", "binding", neck_line_f + neck_line_b,
                 "Обработать горловину косой бейкой или подгибкой."),
        SeamInfo("armhole", "Проймы", "binding", armhole_f + armhole_b,
                 "Обработать обе проймы косой бейкой или подгибкой."),
        SeamInfo("hem", "Подшивка низа", "hem", 0.0,
                 "Обработать нижний срез подгибкой."),
    ]

    binding = (neck_line_f + neck_line_b + armhole_f + armhole_b) * 1.05 + 6.0
    h_max = length + 2.0 * allow + 4.0
    fabric = (150.0, round(h_max * 2.0 + 10.0, 1))

    notes = [
        "Майка рассчитана на трикотаж (кулирка, интерлок, рибана).",
        "Для woven-ткани выберите «свободный крой» и увеличьте прибавки.",
        "Глубину горловины спереди можно менять: стандарт 7.5 см, под грудь — до 12 см.",
    ]

    return DraftResult([p_front, p_back], checks, seams, fabric,
                       [("Косая бейка (кулиска) для горловины и пройм", round(binding, 1))],
                       notes)
