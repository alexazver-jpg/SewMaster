# -*- coding: utf-8 -*-
"""Выкройка: трусы-боксёры (свободные, на резинке, без гульфика).

Переднее и заднее полотнища кроятся на сгибе по средней линии.
Швы: боковые, шаговые (внутренняя сторона штанин), средний шов,
пояс под резинку (кулиска или зигзаг), подшивка низа.
"""
from __future__ import annotations

import math
from typing import Dict

from ..geom import Contour, Pt, dist
from ..piece import (DraftResult, Notch, PatternPiece, PieceLabel, SeamInfo)


def build(m: Dict[str, float], p: Dict[str, object]) -> DraftResult:
    hips = float(m["hips"])
    rise = float(m["rise"])
    side_len = float(m["side_len"])
    thigh = float(m.get("thigh") or hips * 0.62)

    ease = float(p.get("ease", 2.0))
    allow = float(p.get("allowance", 1.0))
    elastic_w = float(p.get("elastic_w", 3.0))

    w = hips / 4.0 + 0.75 + ease / 2.0          # ширина полотнища по талии/бёдрам
    leg_w = thigh / 2.0 + 1.5                    # внутренняя точка низа штанины
    out_w = leg_w + 2.0                          # внешняя точка низа (лёгкое расширение)
    if out_w < w:
        out_w = w

    yc_f = rise - 9.5                            # высота шаговой точки спереди
    yc_b = rise - 8.0                            # сзади
    if yc_f < 10.0:
        yc_f = 10.0
    if yc_b < 11.0:
        yc_b = 11.0
    if side_len < yc_b + 6.0:
        side_len = yc_b + 6.0                    # штанина не короче шага

    def panel(piece_id: str, name: str, cx: float, yc: float,
              ctrl_deep: float) -> PatternPiece:
        A = (0.0, 0.0)
        B = (w, 0.0)
        H_out = (out_w, side_len)
        H_in = (leg_w, side_len)
        C = (cx, yc)
        B0 = (0.0, yc - 1.5)

        c = Contour(A)
        c.line(B)                                              # верхний срез (пояс)
        c.cubic((w + 0.2, side_len * 0.55), (out_w - 0.6, side_len - 3.0), H_out)
        c.line(H_in)                                           # низ штанины
        c.cubic((leg_w - 2.5, side_len - 5.0), (ctrl_deep, yc + 5.5), C)  # шаговый шов
        c.line(B0)                                             # подъём к центру
        c.line(A)                                              # средняя линия (сгиб)

        piece = PatternPiece(piece_id, name, c,
                             "1 деталь со сгибом (сгиб — по средней линии)")
        piece.allowance = allow
        piece.allowance_edges = [allow, allow, allow, allow, allow, 0.0]
        piece.folds = [((0.0, 4.0), (0.0, B0[1] - 1.5))]
        piece.grain = ((w * 0.62, 6.0), (w * 0.62, side_len - 5.0))
        piece.notches = [
            Notch((w, 8.0), 180.0, "метка бокового шва"),
            Notch(C, math.degrees(math.atan2(-5.0, 8.0)), "ластовица"),
        ]
        piece.labels = [PieceLabel((w * 0.5, (yc + side_len) / 2.0 + 1.0),
                                   [name.split()[0], "сгиб по средней линии"],
                                   bold=True)]
        return piece

    p_front = panel("front", "ПЕРЕДНЯЯ ПАНЕЛЬ", 4.5, yc_f, 9.0)
    p_back = panel("back", "ЗАДНЯЯ ПАНЕЛЬ", 6.5, yc_b, 11.5)

    # контрольные длины
    g_front = p_front.contour.seg_groups()
    g_back = p_back.contour.seg_groups()

    def glen(g, idx):
        return sum(dist(g[idx][i], g[idx][i + 1]) for i in range(len(g[idx]) - 1))

    side_f = glen(g_front, 1)
    side_b = glen(g_back, 1)
    inseam_f = glen(g_front, 3)
    inseam_b = glen(g_back, 3)
    mid_f = dist((4.5, yc_f), (0.0, yc_f - 1.5))
    mid_b = dist((6.5, yc_b), (0.0, yc_b - 1.5))

    checks = [
        ("Боковой шов: перед", side_f),
        ("Боковой шов: зад", side_b),
        ("Шаговый шов: перед", inseam_f),
        ("Шаговый шов: зад", inseam_b),
        ("Средний шов: перед + зад", mid_f + mid_b),
        ("Обхват штанины внизу", (out_w + leg_w) * 2.0),
    ]

    seams = [
        SeamInfo("side", "Боковые швы", "side", (side_f + side_b) / 2.0,
                 "Стачать переднюю и заднюю панели по боковым срезам (2 шва)."),
        SeamInfo("inseam", "Шаговые швы", "inseam", (inseam_f + inseam_b) / 2.0,
                 "Стачать передний и задний шаговые срезы каждой штанины (2 шва)."),
        SeamInfo("crotch", "Средний шов", "crotch", mid_f + mid_b,
                 "Стачать нижние средние срезы переда и зада."),
        SeamInfo("waist_elastic", "Пояс под резинку", "elastic", 0.0,
                 "Притачать поясную резинку или выполнить кулиску."),
        SeamInfo("hem", "Подшивка низа штанин", "hem", 0.0,
                 "Обработать нижние срезы штанин."),
    ]

    waist_elastic = hips * 0.9 + 4.0
    elastic = [("Резинка для пояса, ширина %g см" % elastic_w,
                round(waist_elastic + 2.0, 1))]

    h_max = side_len + 2.0 * allow + 4.0
    fabric = (150.0, round(h_max * 2.0 + 10.0, 1))

    notes = [
        "Боксёры можно шить из трикотажа или из лёгких тканей (сатин, байка, поплин).",
        "Для woven-тканей (не тянутся) прибавка по бёдрам уже учтена; пояс — только кулиска с резинкой.",
        "Проверьте обхват штанины внизу: он должен свободно проходить по бедру.",
    ]

    return DraftResult([p_front, p_back], checks, seams, fabric, elastic, notes)
