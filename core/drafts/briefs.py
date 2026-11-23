# -*- coding: utf-8 -*-
"""Выкройка: трусы-слипы (классические, на резинке).

Методика: упрощённое плоское построение по меркам Об (бёдра), От (талия),
Вс (высота сидения). Переднее и заднее полотнища кроятся на сгибе ткани
по средней линии, соединяются боковыми швами и коротким средним швом.
Вырезы ног и пояс обрабатываются резинкой (или окантовкой).

Все размеры — в сантиметрах. Ось Y направлена вниз.
Сегменты контура (для припусков):
  0 — линия талии, 1 — боковой шов, 2 — вырез ноги, 3 — подъём к центру,
  4 — средняя линия (СГИБ, припуск 0).
"""
from __future__ import annotations

import math
from typing import Dict, List

from ..geom import Contour, Pt, dist
from ..piece import (DraftResult, Notch, PatternPiece, PieceLabel, SeamInfo)

# Стиль посадки: изменение высоты сидения, см
WAIST_STYLE = {"classic": 0.0, "high": 2.5, "low": -2.5}


def build(m: Dict[str, float], p: Dict[str, object]) -> DraftResult:
    hips = float(m["hips"])
    waist = float(m["waist"])
    rise = float(m["rise"])

    ease = float(p.get("ease", 1.0))
    rise += WAIST_STYLE.get(str(p.get("waist_style", "classic")), 0.0)
    if rise < 16.0:
        rise = 16.0
    allow = float(p.get("allowance", 1.0))
    elastic_w = float(p.get("elastic_w", 3.0))

    hip_y = 8.0 + hips / 100.0          # уровень линии бёдер
    w_front = hips / 4.0 + 0.25 + ease / 2.0
    w_back = hips / 4.0 + 1.25 + ease / 2.0

    # ---------------- переднее полотнище --------------------------------
    A = (0.0, 3.0)                       # центр талии спереди (занижен)
    B = (w_front, 0.0)                   # боковая точка талии
    Ls = (w_front, hip_y + 3.0)          # начало выреза ноги сбоку
    C = (3.5, rise - 0.5)                # точка ластовицы (шага) спереди
    B0 = (0.0, rise - 3.0)               # нижняя точка средней линии спереди

    front = Contour(A)
    front.cubic((w_front * 0.45, 0.4), (w_front * 0.8, 0.0), B)          # талия
    front.cubic((w_front + 0.3, hip_y * 0.55), (w_front + 0.3, hip_y), Ls)  # боковой шов
    front.cubic((w_front - 1.5, rise - 4.0), (w_front * 0.42, rise - 0.4), C)  # вырез ноги
    front.line(B0)                        # подъём к центру спереди
    front.line(A)                         # средняя линия переда (сгиб)

    p_front = PatternPiece("front", "ПЕРЕДНЕЕ ПОЛОТНИЩЕ", front,
                           "1 деталь со сгибом (сгиб — по средней линии переда)")
    p_front.allowance = allow
    p_front.allowance_edges = [allow, allow, allow, allow, 0.0]
    p_front.folds = [((0.0, A[1] + 2.5), (0.0, B0[1] - 2.0))]
    p_front.grain = ((w_front * 0.60, 7.0), (w_front * 0.60, rise - 7.0))
    p_front.notches = [
        Notch((w_front, hip_y), 180.0, "линия бёдер"),
        Notch(C, math.degrees(math.atan2(-6.0, 8.0)), "ластовица"),
    ]
    p_front.labels = [
        PieceLabel((w_front * 0.45, (A[1] + B0[1]) / 2.0 + 1.5),
                   ["ПЕРЕД", "сгиб по средней линии"], bold=True),
    ]

    # ---------------- заднее полотнище -----------------------------------
    Ab = (0.0, 1.5)
    Bb = (w_back, 0.0)
    Lsb = (w_back, hip_y + 1.5)
    Cb = (5.5, rise + 1.0)
    B0b = (0.0, rise - 1.5)

    back = Contour(Ab)
    back.cubic((w_back * 0.45, 0.3), (w_back * 0.8, 0.0), Bb)
    back.cubic((w_back + 0.4, hip_y * 0.6), (w_back + 0.4, hip_y), Lsb)
    back.cubic((w_back - 1.0, rise - 2.5), (w_back * 0.45, rise + 0.9), Cb)
    back.line(B0b)
    back.line(Ab)

    p_back = PatternPiece("back", "ЗАДНЕЕ ПОЛОТНИЩЕ", back,
                          "1 деталь со сгибом (сгиб — по средней линии зада)")
    p_back.allowance = allow
    p_back.allowance_edges = [allow, allow, allow, allow, 0.0]
    p_back.folds = [((0.0, Ab[1] + 2.5), (0.0, B0b[1] - 2.0))]
    p_back.grain = ((w_back * 0.60, 7.0), (w_back * 0.60, rise - 7.0))
    p_back.notches = [
        Notch((w_back, hip_y), 180.0, "линия бёдер"),
        Notch(Cb, math.degrees(math.atan2(-6.0, 8.0)), "ластовица"),
    ]
    p_back.labels = [
        PieceLabel((w_back * 0.45, (Ab[1] + B0b[1]) / 2.0 + 2.0),
                   ["ЗАДНЯЯ ЧАСТЬ", "сгиб по средней линии"], bold=True),
    ]

    # ---------------- контрольные длины -----------------------------------
    gf = front.seg_groups()
    gb = back.seg_groups()

    def glen(g, idx):
        return sum(dist(g[idx][i], g[idx][i + 1]) for i in range(len(g[idx]) - 1))

    side_len = glen(gf, 1)
    leg_f = glen(gf, 2)
    leg_b = glen(gb, 2)
    mid_f = dist(C, B0)
    mid_b = dist(Cb, B0b)

    checks = [
        ("Боковой шов (перед)", side_len),
        ("Вырез ноги: перед", leg_f),
        ("Вырез ноги: зад", leg_b),
        ("Средний шов: перед + зад", mid_f + mid_b),
    ]

    seams = [
        SeamInfo("side", "Боковые швы", "side", side_len,
                 "Стачать переднее и заднее полотнища по боковым срезам (2 шва)."),
        SeamInfo("crotch", "Средний шов (ластовица)", "crotch", mid_f + mid_b,
                 "Стачать нижние средние срезы переда и зада между точками у ластовицы."),
        SeamInfo("leg_elastic", "Резинка в вырезы ног", "elastic", 0.0,
                 "Обработать оба выреза ноги эластичной тесьмой."),
        SeamInfo("waist_elastic", "Резинка в пояс", "elastic", 0.0,
                 "Обработать верхний срез поясной резинкой."),
    ]

    # ---------------- материалы --------------------------------------------
    leg_elastic = (leg_f + leg_b) * 0.88
    waist_elastic = waist * 0.85 + 3.0
    elastic = [
        ("Резинка для пояса, ширина %g см" % elastic_w, round(waist_elastic + 2.0, 1)),
        ("Резинка для вырезов ног (2 шт. по %g см)" % round(leg_elastic / 2.0, 1),
         round(leg_elastic + 2.0, 1)),
    ]

    h_max = rise + 2.0 + 2.0 * allow
    fabric = (150.0, round(h_max * 2.0 + 10.0, 1))   # ткань 150 см, в 2 слоя

    notes = [
        "Выкройка рассчитана на трикотаж (кулирка, интерлок, рибана) с эластаном.",
        "Если ткань слабо тянется, увеличьте прибавку «свобода облегания» на 1-2 см.",
        "Перед раскроем на дорогой ткани сделайте пробную пару из старой простыни.",
    ]

    return DraftResult([p_front, p_back], checks, seams, fabric, elastic, notes)
