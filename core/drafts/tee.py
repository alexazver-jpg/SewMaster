# -*- coding: utf-8 -*-
"""Выкройка: футболка со спущенным плечом (drop shoulder).

Простая конструкция для новичка: полочка и спинка на сгибе, рукав —
почти прямая деталь без сложного оката. Швы: плечевые, вшивка рукавов,
боковые вместе со швами рукавов, горловина под бейку, подшивка низа.
"""
from __future__ import annotations

import math
from typing import Dict

from ..geom import Contour, Pt, dist
from ..piece import (DraftResult, Notch, PatternPiece, PieceLabel, SeamInfo)

FIT_EASE = {"fit": 4.0, "over": 8.0}   # свобода облегания по груди


def build(m: Dict[str, float], p: Dict[str, object]) -> DraftResult:
    chest = float(m["chest"])
    hips = float(m.get("hips") or chest)
    length = float(m["length"])
    neck = float(m["neck"])
    sleeve_len = float(m["sleeve_len"])
    arm = float(m["arm"])

    fit = str(p.get("fit", "fit"))
    ease = FIT_EASE.get(fit, 4.0)
    allow = float(p.get("allowance", 1.0))

    w = chest / 4.0 + ease / 2.0
    hem_w = max(w, hips / 4.0 + 2.0)
    # Горловина (v1.1.0, исправление): суммарная длина перед+зад должна
    # быть ~0.6x Ош, чтобы голова прошла в ворот с растяжением бейки.
    neck_w = neck / 6.0 + 1.8
    neck_f = neck_w + 3.3
    neck_b = 2.6
    slope = 4.0                                  # скос плеча
    # Пройма: от груди И от обхвата плеча — берём большую глубину,
    # чтобы рукав проходил по руке любой комплекции.
    arm_d = max(chest / 10.0 + 12.0 + (2.0 if fit == "over" else 0.0),
                arm / 2.0 + 8.0)

    def panel(piece_id: str, name: str, neck_depth: float,
              tag: str) -> PatternPiece:
        N0 = (0.0, neck_depth)
        N1 = (neck_w, 0.0)                        # точка горловины на плече
        SP = (w, slope)                           # плечевая точка (края проймы)
        U = (w, arm_d)                            # нижняя точка проймы
        H = (hem_w, length)
        Hc = (0.0, length)

        c = Contour(N0)
        c.cubic((neck_w * 0.4, neck_depth * 0.75), (neck_w * 0.85, 0.0), N1)  # горловина
        c.line(SP)                                                             # плечевой шов
        c.cubic((w + 0.3, slope + 3.0),
                (w - 4.6, arm_d - 5.0), U)                                     # пройма
        c.line(H)                                                              # боковой шов
        c.line(Hc)                                                             # низ
        c.line(N0)                                                             # средняя линия

        piece = PatternPiece(piece_id, name, c,
                             "1 деталь со сгибом (сгиб — по средней линии)")
        piece.allowance = allow
        piece.allowance_edges = [allow, allow, allow, allow, allow, 0.0]
        piece.folds = [((0.0, neck_depth + 3.0), (0.0, length - 3.0))]
        piece.grain = ((w * 0.6, arm_d * 0.5), (w * 0.6, length - 4.0))
        piece.notches = [
            Notch((w, arm_d + 5.0), 180.0, "боковой шов"),
            Notch((w - 2.4, slope + 4.0), math.degrees(math.atan2(-1.0, -3.0)),
                  "метка рукава"),
        ]
        piece.labels = [PieceLabel((w * 0.42, (arm_d + length) / 2.0),
                                   [tag, "сгиб по средней линии"], bold=True)]
        return piece

    p_front = panel("front", "ПОЛОЧКА ФУТБОЛКИ", neck_f, "ПОЛОЧКА (перед)")
    p_back = panel("back", "СПИНКА ФУТБОЛКИ", neck_b, "СПИНКА (зад)")

    # ---------------- рукав (v1.1.0, исправление) -------------------------
    # Пройма-кольцо = пройма полочки + пройма спинки. Окат рукава должен
    # быть равен кольцу (±1 см), иначе рукав не втачать. Труба рукава
    # наверху = ширине детали w_top — должна быть больше обхвата плеча.
    gf = p_front.contour.seg_groups()
    gb = p_back.contour.seg_groups()

    def glen(g, idx):
        return sum(dist(g[idx][i], g[idx][i + 1]) for i in range(len(g[idx]) - 1))

    armhole_f = glen(gf, 2)
    armhole_b = glen(gb, 2)
    ring = armhole_f + armhole_b
    w_top = max(arm + 6.0, ring - 0.2)
    w_bot = arm + 4.0                        # труба короткого рукава — свободно

    TL = (0.0, 2.0)
    TR = (w_top, 2.0)
    BR = ((w_top + w_bot) / 2.0, sleeve_len)
    BL = ((w_top - w_bot) / 2.0, sleeve_len)

    sl = Contour(TL)
    sl.cubic((w_top * 0.3, 0.0), (w_top * 0.7, 0.0), TR)     # верхний край (окат-стрелка)
    sl.line(BR)                                              # передний срез рукава
    sl.line(BL)                                              # низ рукава
    sl.line(TL)                                              # задний срез

    p_sleeve = PatternPiece("sleeve", "РУКАВ", sl, "2 детали (вторая — зеркально)")
    p_sleeve.allowance = allow
    p_sleeve.grain = ((w_top / 2.0, 4.0), (w_top / 2.0, sleeve_len - 3.0))
    p_sleeve.notches = [Notch((w_top / 2.0, 2.6), 90.0, "середина оката")]
    p_sleeve.labels = [PieceLabel((w_top / 2.0, sleeve_len * 0.55),
                                  ["РУКАВ", "2 детали (зеркально)"], bold=True)]

    # контрольные длины
    gs = p_sleeve.contour.seg_groups()

    side_f = glen(gf, 3)
    side_b = glen(gb, 3)
    if abs(side_f - side_b) > 0.05:
        raise AssertionError("Боковые швы полочки и спинки должны совпадать: "
                             "%.3f != %.3f" % (side_f, side_b))
    shoulder = dist((neck_w, 0.0), (w, slope))
    cap_top = glen(gs, 0)
    if abs(cap_top - ring) > 1.5:
        raise AssertionError("Окат рукава (%.1f) должен быть равен пройме-кольцу "
                             "(%.1f)" % (cap_top, ring))

    checks = [
        ("Боковой шов: полочка", side_f),
        ("Боковой шов: спинка", side_b),
        ("Пройма: полочка", armhole_f),
        ("Пройма: спинка", armhole_b),
        ("Пройма-кольцо (перед + зад)", ring),
        ("Окат рукава (должен быть равен кольцу)", cap_top),
        ("Длина плечевого шва", shoulder),
        ("Ширина рукава внизу (труба)", w_bot),
    ]

    seams = [
        SeamInfo("shoulder", "Плечевые швы", "shoulder", shoulder,
                 "Стачать полочку и спинку по плечевым срезам (2 шва)."),
        SeamInfo("sleeve", "Вшивание рукавов", "sleeve", (armhole_f + armhole_b) / 2.0,
                 "Втачать рукава в открытые проймы, совмещая метки (2 шва)."),
        SeamInfo("side", "Боковые швы и швы рукавов", "side", side_f,
                 "Стачать боковые срезы и срезы рукавов одной строчкой (2 шва)."),
        SeamInfo("neck", "Горловина", "neck", 0.0,
                 "Обработать горловину бейкой в кольцо."),
        SeamInfo("hem", "Подшивка низа изделия и рукавов", "hem", 0.0,
                 "Обработать нижние срезы подгибкой."),
    ]

    neck_ring = (neck_line_total(p_front, p_back)) * 0.9
    h_panel = length + 2.0 * allow + 4.0
    fabric_len = h_panel * 2.0 + sleeve_len + 2.0 * allow + 6.0
    fabric = (150.0, round(fabric_len, 1))

    notes = [
        "Футболка рассчитана на трикотаж (кулирка, интерлок, футер).",
        "Конструкция со спущенным плечом: рукав пришивается к прямому верху проймы — это самый простой вариант для первой вещи.",
        "Бейку горловины выкраивайте из рибаны шириной 5-6 см и длиной по контрольной мерке горловины x0.9.",
    ]

    elastic = [("Бейка для горловины (рибана, полоса 5-6 см)", round(neck_ring + 4.0, 1))]

    return DraftResult([p_front, p_back, p_sleeve], checks, seams, fabric,
                       elastic, notes)


def neck_line_total(p_front: PatternPiece, p_back: PatternPiece) -> float:
    """Полная длина горловины (перед + зад)."""
    def neck_len(piece: PatternPiece) -> float:
        g = piece.contour.seg_groups()
        seg = g[0]
        return sum(dist(seg[i], seg[i + 1]) for i in range(len(seg) - 1))
    return neck_len(p_front) + neck_len(p_back)
