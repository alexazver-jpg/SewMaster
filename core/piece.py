# -*- coding: utf-8 -*-
"""Деталь выкройки и результат построения модели."""
from __future__ import annotations

import copy
from typing import Dict, List, Optional, Tuple

from .geom import Contour, Pt, dist, polygon_bbox


class Notch(object):
    """Насечка (метка совмещения деталей) в точке с направлением внутрь детали."""

    def __init__(self, pt: Pt, angle_deg: float, label: str = ""):
        self.pt = pt
        self.angle_deg = angle_deg  # направление внутрь детали, градусы
        self.label = label


class PieceLabel(object):
    """Текстовый блок на детали (название, крой, размер...)."""

    def __init__(self, pt: Pt, lines: List[str], bold: bool = False):
        self.pt = pt
        self.lines = lines
        self.bold = bold


class PatternPiece(object):
    """Деталь выкройки.

    contour  — линия шва (замкнутый контур),
    cut_poly — линия кроя (контур + припуск), вычисляется лениво.
    """

    def __init__(self, piece_id: str, name: str, contour: Contour,
                 cut_note: str = "1 деталь со сгибом",
                 fabric_note: str = "трикотаж"):
        self.piece_id = piece_id
        self.name = name
        self.contour = contour
        self.cut_note = cut_note          # например: "1 деталь со сгибом" / "2 детали"
        self.fabric_note = fabric_note
        self.allowance = 1.0              # припуск на швы, см
        self.allowance_edges = None       # type: Optional[List[float]]
                                         # припуски по сегментам контура
                                         # (0 на краях «сгиб»)
        self.notches = []                 # type: List[Notch]
        self.folds = []                   # type: List[Tuple[Pt, Pt]]  # линии сгиба
        self.grain = None                 # type: Optional[Tuple[Pt, Pt]]  # долевая
        self.labels = []                  # type: List[PieceLabel]
        self._cut_poly = None             # type: Optional[List[Pt]]

    # ---- припуски -----------------------------------------------------
    @property
    def cut_poly(self) -> List[Pt]:
        if self._cut_poly is None:
            if self.allowance_edges is not None:
                self._cut_poly = self.contour.offset_multi(self.allowance_edges)
            else:
                self._cut_poly = self.contour.offset(self.allowance)
        return self._cut_poly

    def invalidate(self):
        self._cut_poly = None

    # ---- размеры -------------------------------------------------------
    def bbox(self, with_cut: bool = True) -> Tuple[float, float, float, float]:
        if with_cut:
            return polygon_bbox(self.cut_poly)
        return self.contour.bbox()

    def size_text(self) -> str:
        x0, y0, x1, y1 = self.bbox(True)
        return "%.0f x %.0f см" % ((x1 - x0), (y1 - y0))

    def contour_length(self) -> float:
        return self.contour.length()

    # ---- размещение на листе -------------------------------------------
    def placed(self, dx: float, dy: float) -> "PatternPiece":
        """Копия детали, сдвинутая на (dx, dy) — для раскладки на страницах PDF."""
        p = copy.deepcopy(self)
        p.contour = self.contour.translated(dx, dy)
        p._cut_poly = None
        p.allowance_edges = list(self.allowance_edges) if self.allowance_edges is not None else None
        p.notches = [Notch((n.pt[0] + dx, n.pt[1] + dy), n.angle_deg, n.label)
                     for n in self.notches]
        p.folds = [((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy))
                   for (a, b) in self.folds]
        if self.grain is not None:
            p.grain = ((self.grain[0][0] + dx, self.grain[0][1] + dy),
                       (self.grain[1][0] + dx, self.grain[1][1] + dy))
        p.labels = [PieceLabel((l.pt[0] + dx, l.pt[1] + dy), list(l.lines), l.bold)
                    for l in self.labels]
        return p


class SeamInfo(object):
    """Шов модели — используется генератором инструкции."""

    def __init__(self, seam_id: str, title: str, kind: str, length_cm: float = 0.0,
                 note: str = ""):
        self.seam_id = seam_id
        self.title = title
        self.kind = kind      # тип шва: side, crotch, inseam, shoulder, neck,
                              # hem, sleeve, elastic, binding ...
        self.length_cm = length_cm
        self.note = note


class DraftResult(object):
    """Итог построения: детали, контрольные длины, швы, расход материалов."""

    def __init__(self, pieces: List[PatternPiece], checks: List[Tuple[str, float]],
                 seams: List[SeamInfo], fabric: Tuple[float, float],
                 elastic: List[Tuple[str, float]], notes: List[str]):
        self.pieces = pieces
        self.checks = checks        # [('Боковой шов', 28.5), ...]
        self.seams = seams
        self.fabric = fabric        # (ширина ткани, длина ткани) в см
        self.elastic = elastic      # [('резинка в пояс', 74), ...]
        self.notes = notes
