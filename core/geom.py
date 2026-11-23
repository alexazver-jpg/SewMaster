# -*- coding: utf-8 -*-
"""Геометрия выкроек: точки, контуры (отрезки и кривые Безье), припуски на швы.

Соглашения:
  * Все координаты в сантиметрах.
  * Ось Y направлена ВНИЗ (как на экране): y=0 — верх детали.
  * Контур (Contour) всегда замкнутый: последний сегмент стыкуется с точкой старта.
  * Припуск (offset) строится наружу от контура, углы скругляются радиусом припуска.
"""
from __future__ import annotations

import math
from typing import List, Tuple

Pt = Tuple[float, float]


def pt_add(a: Pt, b: Pt) -> Pt:
    return (a[0] + b[0], a[1] + b[1])


def pt_sub(a: Pt, b: Pt) -> Pt:
    return (a[0] - b[0], a[1] - b[1])


def pt_mul(a: Pt, k: float) -> Pt:
    return (a[0] * k, a[1] * k)


def pt_len(a: Pt) -> float:
    return math.hypot(a[0], a[1])


def pt_norm(a: Pt) -> Pt:
    l = pt_len(a)
    if l < 1e-12:
        return (0.0, 0.0)
    return (a[0] / l, a[1] / l)


def dist(a: Pt, b: Pt) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def cubic_at(p0: Pt, c1: Pt, c2: Pt, p1: Pt, t: float) -> Pt:
    """Точка на кубической кривой Безье (t в диапазоне 0..1)."""
    mt = 1.0 - t
    a = mt * mt * mt
    b = 3.0 * mt * mt * t
    c = 3.0 * mt * t * t
    d = t * t * t
    return (a * p0[0] + b * c1[0] + c * c2[0] + d * p1[0],
            a * p0[1] + b * c1[1] + c * c2[1] + d * p1[1])


def polygon_area(pts: List[Pt]) -> float:
    """Знаковая площадь многоугольника (формула шнурования)."""
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def polygon_bbox(pts: List[Pt]) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _line_intersection(p1: Pt, d1: Pt, p2: Pt, d2: Pt) -> Pt:
    """Пересечение прямых p1+t*d1 и p2+s*d2 (или None, если параллельны)."""
    det = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(det) < 1e-9:
        return None
    dp = pt_sub(p2, p1)
    t = (dp[0] * d2[1] - dp[1] * d2[0]) / det
    return (p1[0] + t * d1[0], p1[1] + t * d1[1])


class Contour(object):
    """Замкнутый контур детали: линия шва (без припусков).

    Сегменты:
      ('L', end)                      — отрезок
      ('C', c1, c2, end)              — кубическая кривая Безье
    """

    def __init__(self, start: Pt):
        self.start = start
        self.cur = start
        self.segs = []  # type: List[tuple]

    # ---- построение -----------------------------------------------------
    def line(self, p: Pt) -> "Contour":
        self.segs.append(("L", p))
        self.cur = p
        return self

    def cubic(self, c1: Pt, c2: Pt, p: Pt) -> "Contour":
        self.segs.append(("C", c1, c2, p))
        self.cur = p
        return self

    # ---- выборка ---------------------------------------------------------
    def points(self, steps: int = 24) -> List[Pt]:
        """Дискретизация контура замкнутым многоугольником (без повтора первой точки)."""
        pts = [self.start]
        cur = self.start
        for s in self.segs:
            if s[0] == "L":
                pts.append(s[1])
                cur = s[1]
            else:
                _, c1, c2, p = s
                for i in range(1, steps + 1):
                    pts.append(cubic_at(cur, c1, c2, p, i / float(steps)))
                cur = p
        return pts

    def seg_groups(self, steps: int = 24) -> List[List[Pt]]:
        """Список полилиний по одному на сегмент (для длин отдельных участков)."""
        groups = []
        cur = self.start
        for s in self.segs:
            if s[0] == "L":
                groups.append([cur, s[1]])
                cur = s[1]
            else:
                _, c1, c2, p = s
                g = [cur]
                for i in range(1, steps + 1):
                    g.append(cubic_at(cur, c1, c2, p, i / float(steps)))
                groups.append(g)
                cur = p
        return groups

    def length(self, steps: int = 24) -> float:
        total = 0.0
        for g in self.seg_groups(steps):
            for i in range(len(g) - 1):
                total += dist(g[i], g[i + 1])
        return total

    def bbox(self, steps: int = 24) -> Tuple[float, float, float, float]:
        return polygon_bbox(self.points(steps))

    # ---- преобразования ---------------------------------------------------
    def translated(self, dx: float, dy: float) -> "Contour":
        c = Contour((self.start[0] + dx, self.start[1] + dy))
        for s in self.segs:
            if s[0] == "L":
                c.line((s[1][0] + dx, s[1][1] + dy))
            else:
                _, c1, c2, p = s
                c.cubic((c1[0] + dx, c1[1] + dy), (c2[0] + dx, c2[1] + dy),
                        (p[0] + dx, p[1] + dy))
        return c

    def mirrored_y(self, axis_x: float) -> "Contour":
        """Отражение относительно вертикальной прямой x = axis_x (меняет обход)."""
        def m(p: Pt) -> Pt:
            return (2.0 * axis_x - p[0], p[1])
        c = Contour(m(self.start))
        for s in self.segs:
            if s[0] == "L":
                c.line(m(s[1]))
            else:
                _, c1, c2, p = s
                c.cubic(m(c1), m(c2), m(p))
        return c

    # ---- припуски ----------------------------------------------------------
    def _offset_group(self, g: List[Pt], d: float) -> List[Pt]:
        """Смещение полилинии на d вдоль нормалей (внутренние точки — центральная разность)."""
        m = len(g)
        out = []
        for j in range(m):
            if m < 2:
                out.append(g[0])
                continue
            if j == 0:
                t = pt_sub(g[1], g[0])
            elif j == m - 1:
                t = pt_sub(g[m - 1], g[m - 2])
            else:
                t = pt_sub(g[j + 1], g[j - 1])
            nv = pt_norm((t[1], -t[0]))
            out.append((g[j][0] + d * nv[0], g[j][1] + d * nv[1]))
        return out

    def offset_multi(self, allowances: List[float], steps: int = 24) -> List[Pt]:
        """Контур линии кроя с индивидуальным припуском на каждый СЕГМЕНТ.

        allowances[i] — припуск сегмента i (в см); 0 — без припуска (например,
        край «сгиб»). На углах между смещёнными сегментами строится «клин»
        (miter join, длина <= 3 припусков), при слишком остром угле — фаска.
        """
        if len(allowances) != len(self.segs):
            raise ValueError("offset_multi: количество припусков != количество сегментов")
        groups = self.seg_groups(steps)
        n = len(groups)
        if not groups:
            return self.points(steps)

        # Определяем знак наружной нормали по равномерному тестовому смещению
        d_test = max([abs(a) for a in allowances] + [1e-6])
        test_plus = []
        test_minus = []
        for g in groups:
            test_plus.extend(self._offset_group(g, +d_test))
            test_minus.extend(self._offset_group(g, -d_test))
        if abs(polygon_area(test_plus)) >= abs(polygon_area(test_minus)):
            sign = 1.0
        else:
            sign = -1.0

        # Смещённые полилинии по сегментам: (припуск, полилиния)
        seg_off = []
        for i, g in enumerate(groups):
            d = allowances[i]
            if abs(d) < 1e-9:
                seg_off.append((0.0, list(g)))
            else:
                seg_off.append((abs(d), self._offset_group(g, d * sign)))

        def miter_point(i_prev: int, i_cur: int) -> Pt:
            """Клин на стыке сегментов (или None — оставить фаску)."""
            d_prev, _ = seg_off[i_prev]
            d_cur, _ = seg_off[i_cur]
            if d_prev <= 1e-9 or d_cur <= 1e-9:
                return None
            g_prev = groups[i_prev]
            g_cur = groups[i_cur]
            if len(g_prev) < 2 or len(g_cur) < 2:
                return None
            t_prev = pt_sub(g_prev[-1], g_prev[-2])   # направление в конце prev
            t_cur = pt_sub(g_cur[1], g_cur[0])        # направление в начале cur
            m = _line_intersection(seg_off[i_prev][1][-1], t_prev,
                                   seg_off[i_cur][1][0], t_cur)
            if m is None:
                return None
            vertex = g_prev[-1]
            if dist(m, vertex) <= 3.0 * max(d_prev, d_cur):
                return m
            return None

        out = []  # type: List[Pt]
        out.extend(seg_off[0][1])
        for i in range(1, n):
            m = miter_point(i - 1, i)
            if m is not None:
                if out and dist(out[-1], seg_off[i - 1][1][-1]) < 1e-9:
                    out[-1] = m            # заменяем конец prev на вершину клина
                else:
                    out.append(m)
                out.extend(seg_off[i][1][1:])
            else:
                first = seg_off[i][1][0]
                if not out or dist(out[-1], first) > 1e-9:
                    out.append(first)
                out.extend(seg_off[i][1][1:])

        # замыкание: стык последнего сегмента с первым
        if n > 1:
            m = miter_point(n - 1, 0)
            if m is not None:
                if dist(out[-1], seg_off[n - 1][1][-1]) < 1e-9:
                    out[-1] = m
                if dist(out[0], seg_off[0][1][0]) < 1e-9:
                    out[0] = m
        return out

    def offset(self, d: float, steps: int = 24) -> List[Pt]:
        """Контур линии кроя: равномерный припуск d см наружу."""
        if abs(d) < 1e-9:
            return self.points(steps)
        return self.offset_multi([d] * len(self.segs), steps)


def polygon_contour(pts: List[Pt]) -> Contour:
    """Контур из полилинии (замыкается автоматически)."""
    c = Contour(pts[0])
    for p in pts[1:]:
        c.line(p)
    return c


def poly_len(pts: List[Pt]) -> float:
    return sum(dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
