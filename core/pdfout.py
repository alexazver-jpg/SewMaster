# -*- coding: utf-8 -*-
"""Экспорт выкройки и инструкции в PDF для печати на A4.

Особенности:
  * масштаб 1:1 (реальный размер), контрольный квадрат 10x10 см на титуле;
  * разбивка больших деталей на листы A4 с метками совмещения (круглые метки
    на серединах стыкуемых сторон) и линиями обрезки по углам;
  * сплошная линия — контур кроя, пунктир — линия шва;
  * печатаются долевая, сгибы, насечки и надписи деталей;
  * лёгкая сетка 10x10 см для визуального контроля масштаба;
  * инструкция по шитью — теми же страницами A4 в этом же файле.

Важно: reportlab завершает страницу по showPage(), поэтому каждая функция
рисует контент СНАЧАЛА и только потом вызывает show_page() (механизм
dirty-флага не даёт появляться пустым страницам).

Координаты деталей — в сантиметрах, ось Y вниз; при отрисовке переводятся
в миллиметры с инверсией Y (PDF использует Y вверх).
"""
from __future__ import annotations

import math
import os
from typing import Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas

from .instructions import build_instructions
from .models import ModelDef
from .piece import DraftResult, PatternPiece
from .paths import APP_VERSION, APP_NAME, asset_path
from .sewing import get_machine

PAGE_W = 210.0        # мм
PAGE_H = 297.0        # мм
MARGIN = 10.0         # мм, непечатаемое поле страницы
CELL_W = PAGE_W - 2 * MARGIN   # 190 мм — рабочая зона листа
CELL_H = PAGE_H - 2 * MARGIN   # 277 мм

CUT_COLOR = HexColor("#111827")     # линия кроя
SEAM_COLOR = HexColor("#dc2626")    # линия шва
GRID_COLOR = HexColor("#d1d5db")    # сетка 10 см
MARK_COLOR = HexColor("#2563eb")    # метки совмещения
FOLD_COLOR = HexColor("#7c3aed")    # сгиб
GRAIN_COLOR = HexColor("#15803d")   # долевая
NOTCH_COLOR = HexColor("#b45309")   # насечки
TEXT_COLOR = HexColor("#111827")
GRAY = HexColor("#6b7280")
BLUE = HexColor("#1d4ed8")

_FONTS_REGISTERED = False


def register_fonts() -> Tuple[str, str]:
    """Регистрирует DejaVuSans (кириллица). Возвращает (regular, bold)."""
    global _FONTS_REGISTERED
    if not _FONTS_REGISTERED:
        pdfmetrics.registerFont(TTFont("DejaVu", asset_path("fonts", "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", asset_path("fonts", "DejaVuSans-Bold.ttf")))
        _FONTS_REGISTERED = True
    return "DejaVu", "DejaVu-Bold"


def wrap_text(text: str, font: str, size: float, max_w: float) -> List[str]:
    """Перенос строк по ширине (мм)."""
    out = []
    for para in text.split("\n"):
        if not para.strip():
            out.append("")
            continue
        words = para.split(" ")
        cur = ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if pdfmetrics.stringWidth(trial, font, size) <= max_w:
                cur = trial
            else:
                if cur:
                    out.append(cur)
                cur = wd
        if cur:
            out.append(cur)
    return out


PT_PER_MM = 72.0 / 25.4   # перевод миллиметров в пункты reportlab


class PdfDraw(object):
    """Обёртка над reportlab canvas: координаты в мм, ось Y вниз."""

    def __init__(self, path: str):
        self.c = pdfcanvas.Canvas(path, pagesize=A4)
        self.c.scale(PT_PER_MM, PT_PER_MM)   # 1 единица = 1 мм
        self.c.setTitle("%s — выкройка" % APP_NAME)
        self.c.setAuthor(APP_NAME)
        self.reg, self.bold = register_fonts()
        self.page_no = 0
        self.dirty = False

    def _y(self, y_mm_down: float) -> float:
        return PAGE_H - y_mm_down

    def _touch(self):
        self.dirty = True

    # ---- примитивы ------------------------------------------------------
    def line(self, p1, p2, color, width=0.35, dash=None):
        c = self.c
        c.saveState()
        c.setStrokeColor(color)
        c.setLineWidth(width)
        if dash:
            c.setDash(dash)
        c.line(p1[0], self._y(p1[1]), p2[0], self._y(p2[1]))
        c.restoreState()
        self._touch()

    def polyline(self, pts, color, width=0.35, dash=None, close=False):
        if not pts:
            return
        c = self.c
        c.saveState()
        c.setStrokeColor(color)
        c.setLineWidth(width)
        if dash:
            c.setDash(dash)
        p = c.beginPath()
        p.moveTo(pts[0][0], self._y(pts[0][1]))
        for q in pts[1:]:
            p.lineTo(q[0], self._y(q[1]))
        if close:
            p.close()
        c.drawPath(p, stroke=1, fill=0)
        c.restoreState()
        self._touch()

    def polygon_fill(self, pts, fill_color, stroke_color=None, width=0.0):
        if not pts:
            return
        c = self.c
        c.saveState()
        p = c.beginPath()
        p.moveTo(pts[0][0], self._y(pts[0][1]))
        for q in pts[1:]:
            p.lineTo(q[0], self._y(q[1]))
        p.close()
        if fill_color is not None:
            c.setFillColor(fill_color)
        if stroke_color is not None:
            c.setStrokeColor(stroke_color)
            c.setLineWidth(width or 0.2)
            c.drawPath(p, stroke=1, fill=1 if fill_color is not None else 0)
        else:
            c.drawPath(p, stroke=0, fill=1)
        c.restoreState()
        self._touch()

    def text(self, pos, s, size_mm=3.0, font=None, color=TEXT_COLOR,
             align="left"):
        c = self.c
        c.saveState()
        c.setFillColor(color)
        font_name = font or self.reg
        c.setFont(font_name, size_mm)
        for i, ln in enumerate(s.split("\n")):
            x, y = pos[0], self._y(pos[1]) - i * size_mm * 1.35
            if align == "center":
                x -= pdfmetrics.stringWidth(ln, font_name, size_mm) / 2.0
            elif align == "right":
                x -= pdfmetrics.stringWidth(ln, font_name, size_mm)
            c.drawString(x, y, ln)
        c.restoreState()
        self._touch()

    def text_vert(self, pos, s, size_mm=2.8, font=None, color=GRAY):
        """Вертикальный текст (сверху вниз)."""
        c = self.c
        c.saveState()
        c.setFillColor(color)
        c.setFont(font or self.reg, size_mm)
        c.translate(pos[0], self._y(pos[1]))
        c.rotate(-90)
        c.drawString(0, 0, s)
        c.restoreState()
        self._touch()

    def circle(self, center, r, color, width=0.3, fill=None):
        c = self.c
        c.saveState()
        c.setStrokeColor(color)
        c.setLineWidth(width)
        if fill is not None:
            c.setFillColor(fill)
        c.circle(center[0], self._y(center[1]), r,
                 stroke=1, fill=1 if fill is not None else 0)
        c.restoreState()
        self._touch()

    def clip_rect(self, x0, y0, w, h):
        c = self.c
        p = c.beginPath()
        p.rect(x0, self._y(y0 + h), w, h)
        c.clipPath(p, stroke=0, fill=0)
        self._touch()

    def save_state(self):
        self.c.saveState()

    def restore_state(self):
        self.c.restoreState()

    def show_page(self):
        """Завершает страницу, если на ней что-то нарисовано.

        ВАЖНО: showPage() сбрасывает графическое состояние (в т.ч. масштаб),
        поэтому после него нужно заново применить масштаб мм.
        """
        if self.dirty:
            self.c.showPage()
            self.page_no += 1
            self.dirty = False
            self.c.scale(PT_PER_MM, PT_PER_MM)

    def save(self):
        self.show_page()
        self.c.save()


# ============================ отрисовка детали ============================

def _pt_cm_to_mm(p) -> Tuple[float, float]:
    return (p[0] * 10.0, p[1] * 10.0)


def draw_piece(d: PdfDraw, piece: PatternPiece, origin_mm: Tuple[float, float]):
    """Рисует деталь (в мм) со сдвигом origin_mm (вычитается)."""
    ox, oy = origin_mm

    def T(p):
        x, y = _pt_cm_to_mm(p)
        return (x - ox, y - oy)

    cut = [T(p) for p in piece.cut_poly]
    d.polygon_fill(cut, HexColor("#eef2ff"))
    d.polyline(cut, CUT_COLOR, width=0.55, close=True)

    seam = [T(p) for p in piece.contour.points(20)] + [T(piece.contour.start)]
    d.polyline(seam, SEAM_COLOR, width=0.3, dash=[2.2, 1.6], close=True)

    for (a, b) in piece.folds:
        d.line(T(a), T(b), FOLD_COLOR, width=0.4, dash=[4, 1.5, 1, 1.5])
    if piece.folds:
        a, b = piece.folds[0]
        m = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        d.text_vert((T(m)[0] - 1.2, T(m)[1]), "СГИБ", 2.6, d.reg, FOLD_COLOR)

    if piece.grain:
        a, b = T(piece.grain[0]), T(piece.grain[1])
        d.line(a, b, GRAIN_COLOR, width=0.4)
        for (p1, p2) in ((a, b), (b, a)):
            ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
            L, Wd = 3.0, 1.2
            for sgn in (-1, 1):
                dx = p1[0] - L * math.cos(ang) - sgn * Wd * math.sin(ang)
                dy = p1[1] - L * math.sin(ang) + sgn * Wd * math.cos(ang)
                d.line(p1, (dx, dy), GRAIN_COLOR, width=0.4)
        d.text_vert(((a[0] + b[0]) / 2.0 + 1.8, (a[1] + b[1]) / 2.0),
                    "ДОЛЕВАЯ (вдоль кромки ткани)", 2.4, d.reg, GRAIN_COLOR)

    for n in piece.notches:
        p = T(n.pt)
        ang = math.radians(n.angle_deg)
        dirv = (math.cos(ang), math.sin(ang))
        allow_mm = (piece.allowance or 1.0) * 10.0
        p_in = (p[0] + dirv[0] * 3.5, p[1] + dirv[1] * 3.5)
        p_out = (p[0] - dirv[0] * (allow_mm + 2.5), p[1] - dirv[1] * (allow_mm + 2.5))
        d.line(p_in, p_out, NOTCH_COLOR, width=0.35)

    for lbl in piece.labels:
        base = T(lbl.pt)
        font = d.bold if lbl.bold else d.reg
        dy = 0.0
        for i, line_text in enumerate(lbl.lines):
            d.text((base[0], base[1] + dy), line_text, 3.2 if lbl.bold else 2.8,
                   font, CUT_COLOR, align="center")
            dy += 4.2 if i == 0 else 3.6


# ============================ служебные элементы страницы ============================

def _page_chrome(d: PdfDraw, header: str, subheader: str = ""):
    d.text((MARGIN, MARGIN - 6.5), header, 2.8, d.bold, TEXT_COLOR)
    if subheader:
        w = pdfmetrics.stringWidth(subheader, d.reg, 2.8)
        d.text((PAGE_W - MARGIN - w, MARGIN - 6.5), subheader, 2.8, d.reg, GRAY)
    d.text((MARGIN, PAGE_H - MARGIN + 9.5),
           "Печатайте в масштабе 100% («реальный размер»). Сплошная линия — "
           "линия кроя, пунктир — линия шва.", 2.5, d.reg, GRAY)


def _crop_marks(d: PdfDraw):
    x0, y0, x1, y1 = MARGIN, MARGIN, MARGIN + CELL_W, MARGIN + CELL_H
    tick = 6.0
    off = 1.5
    for (cx, cy, dx, dy) in (
            (x0, y0, -1, -1), (x1, y0, 1, -1), (x0, y1, -1, 1), (x1, y1, 1, 1)):
        d.line((cx + dx * off, cy), (cx + dx * (off + tick), cy), MARK_COLOR, 0.25)
        d.line((cx, cy + dy * off), (cx, cy + dy * (off + tick)), MARK_COLOR, 0.25)


def _align_marks(d: PdfDraw, col: int, row: int, cols: int, rows: int):
    """Круглые метки совмещения на серединах стыкуемых сторон листа."""
    x0, y0 = MARGIN, MARGIN
    x1, y1 = MARGIN + CELL_W, MARGIN + CELL_H
    r = 3.5
    if col + 1 < cols:
        center = (x1, (y0 + y1) / 2.0)
        d.circle(center, r, MARK_COLOR, 0.35, fill=HexColor("#dbeafe"))
        d.line((center[0] - r - 2, center[1]), (center[0] + r + 2, center[1]),
               MARK_COLOR, 0.3)
        d.line((center[0], center[1] - r - 2), (center[0], center[1] + r + 2),
               MARK_COLOR, 0.3)
        d.text((MARGIN + 2, (y0 + y1) / 2.0 + 6.0), "→ круглая метка: "
               "к ней приклеится следующий лист", 2.4, d.reg, MARK_COLOR)
    if row + 1 < rows:
        center = ((x0 + x1) / 2.0, y1)
        d.circle(center, r, MARK_COLOR, 0.35, fill=HexColor("#dbeafe"))
        d.line((center[0] - r - 2, center[1]), (center[0] + r + 2, center[1]),
               MARK_COLOR, 0.3)
        d.line((center[0], center[1] - r - 2), (center[0], center[1] + r + 2),
               MARK_COLOR, 0.3)


def _grid_10cm(d: PdfDraw, ox_mm: float, oy_mm: float):
    """Лёгкая сетка каждые 10 см (в системе координат детали)."""
    step = 100.0
    k = math.floor(ox_mm / step) * step
    while k <= ox_mm + CELL_W:
        if k >= ox_mm:
            d.line((k - ox_mm + MARGIN, MARGIN),
                   (k - ox_mm + MARGIN, MARGIN + CELL_H), GRID_COLOR, 0.15)
        k += step
    k = math.floor(oy_mm / step) * step
    while k <= oy_mm + CELL_H:
        if k >= oy_mm:
            d.line((MARGIN, k - oy_mm + MARGIN),
                   (MARGIN + CELL_W, k - oy_mm + MARGIN), GRID_COLOR, 0.15)
        k += step


# ============================ страницы детали ============================

def _piece_page_count(piece: PatternPiece) -> int:
    x0, y0, x1, y1 = piece.bbox(True)
    cols = max(1, int(math.ceil((x1 - x0) * 10.0 / CELL_W - 1e-9)))
    rows = max(1, int(math.ceil((y1 - y0) * 10.0 / CELL_H - 1e-9)))
    return cols * rows


def _draw_piece_page(d: PdfDraw, piece: PatternPiece, col: int, row: int,
                     cols: int, rows: int, model_title: str,
                     counter: int, total: int):
    ox = col * CELL_W
    oy = row * CELL_H
    _page_chrome(d, "%s · %s" % (model_title, piece.name),
                 "Лист %d из %d" % (counter, total))
    _crop_marks(d)
    _align_marks(d, col, row, cols, rows)

    d.save_state()
    d.clip_rect(MARGIN, MARGIN, CELL_W, CELL_H)
    _grid_10cm(d, ox, oy)
    draw_piece(d, piece, (ox - MARGIN, oy - MARGIN))
    d.restore_state()
    d.show_page()


def _piece_pages(d: PdfDraw, piece: PatternPiece, model_title: str,
                 counter: List[int], total: int):
    x0, y0, x1, y1 = piece.bbox(True)
    cols = max(1, int(math.ceil((x1 - x0) * 10.0 / CELL_W - 1e-9)))
    rows = max(1, int(math.ceil((y1 - y0) * 10.0 / CELL_H - 1e-9)))
    placed = piece.placed(-x0, -y0)
    for row in range(rows):
        for col in range(cols):
            counter[0] += 1
            _draw_piece_page(d, placed, col, row, cols, rows, model_title,
                             counter[0], total)


# ============================ титульная страница ============================

def _title_page(d: PdfDraw, model: ModelDef, meas: Dict[str, float],
                params: Dict[str, object], draft: DraftResult,
                machine_key: str, size_label: str):
    y = 16.0
    col_w = 95.0        # ширина левой текстовой колонки (титул)
    right_x = MARGIN + col_w + 8.0

    d.text((MARGIN, y), APP_NAME, 6.2, d.bold, BLUE)
    d.text((PAGE_W - MARGIN, y + 0.6), "v" + APP_VERSION, 3.0, d.reg, GRAY,
           align="right")
    y += 9.5
    d.text((MARGIN, y), "конструктор выкроек для домашнего пошива", 3.2, d.reg, GRAY)
    y += 6.0
    d.line((MARGIN, y), (PAGE_W - MARGIN, y), BLUE, 0.8)
    y += 8.0

    d.text((MARGIN, y), model.title, 7.2, d.bold, TEXT_COLOR)
    y += 9.5
    for ln in wrap_text(model.description, d.reg, 3.1, PAGE_W - 2 * MARGIN)[:3]:
        d.text((MARGIN, y), ln, 3.1, d.reg, GRAY)
        y += 4.6
    y += 5.0

    # ---- левая колонка: мерки, параметры, машина ----
    def section(title):
        nonlocal y
        d.text((MARGIN, y), title, 3.5, d.bold, BLUE)
        y += 5.8

    section("Мерки%s, см:" % ((" (" + size_label + ")") if size_label else ""))
    for f in model.measurements:
        val = meas.get(f.key)
        if val is None:
            continue
        d.text((MARGIN + 2.0, y), "%s — %g" % (f.label, val), 3.0)
        y += 5.2
    y += 4.0

    section("Параметры построения:")
    for pf in model.params:
        val = params.get(pf.key, pf.default)
        if pf.choices:
            choice = next((c.label for c in pf.choices if c.value == val), str(val))
        else:
            choice = "%g см" % val
        d.text((MARGIN + 2.0, y), "%s — %s" % (pf.label, choice), 3.0)
        y += 5.2
    y += 4.0

    machine = get_machine(machine_key)
    section("Швейная машина: %s" % machine.title)
    for ln in wrap_text(machine.description, d.reg, 2.8, col_w)[:2]:
        d.text((MARGIN + 2.0, y), ln, 2.8, d.reg, GRAY)
        y += 4.4
    y += 4.0

    section("Детали выкройки (с припусками):")
    for piece in draft.pieces:
        d.text((MARGIN + 2.0, y), "• %s — %s, %s" %
               (piece.name, piece.size_text(), piece.cut_note), 3.0)
        y += 5.2
    y += 4.0

    section("Расход материалов:")
    d.text((MARGIN + 2.0, y), "Ткань: %g см при ширине %g см"
           % (draft.fabric[1], draft.fabric[0]), 3.0)
    y += 5.2
    for name, length in draft.elastic:
        for ln in wrap_text("%s — %g см" % (name, length), d.reg, 3.0, col_w)[:1]:
            d.text((MARGIN + 2.0, y), ln, 3.0)
            y += 5.2

    # ---- правая колонка: контрольный квадрат ----
    sq = 100.0
    qx, qy = PAGE_W - MARGIN - sq, 120.0
    d.polygon_fill([(qx, qy), (qx + sq, qy), (qx + sq, qy + sq), (qx, qy + sq)],
                   None, CUT_COLOR, 0.6)
    d.line((qx + sq / 2, qy), (qx + sq / 2, qy + sq), GRID_COLOR, 0.2)
    d.line((qx, qy + sq / 2), (qx + sq, qy + sq / 2), GRID_COLOR, 0.2)
    d.text((qx + sq / 2, qy - 7.0), "КОНТРОЛЬНЫЙ КВАДРАТ 10 × 10 см", 3.0,
           d.bold, CUT_COLOR, align="center")
    for i, ln in enumerate(["Измерьте сторону линейкой.",
                            "Не 10 см — проверьте масштаб",
                            "печати (должно быть 100%)."]):
        d.text((qx + sq / 2, qy + sq + 6.0 + i * 4.4), ln, 2.7, d.reg, GRAY,
               align="center")

    # ---- низ: сборка листов ----
    y2 = 246.0
    d.line((MARGIN, y2 - 7.0), (PAGE_W - MARGIN, y2 - 7.0), GRID_COLOR, 0.4)
    d.text((MARGIN, y2), "Как собрать выкройку из листов:", 3.8, d.bold, BLUE)
    y2 += 6.5
    for line in [
        "1. Распечатайте все листы в масштабе 100% (двусторонняя печать не нужна).",
        "2. Проверьте контрольный квадрат линейкой.",
        "3. Обрежьте каждый лист по линиям обрезки (угловые метки).",
        "4. Склейте листы встык, совмещая круглые метки на краях листов.",
        "5. Вырезайте детали по СПЛОШНОЙ линии. Пунктир — линия шва.",
    ]:
        d.text((MARGIN + 2.0, y2), line, 3.0)
        y2 += 5.4

    if draft.notes:
        y2 += 2.0
        for note in draft.notes[:3]:
            for ln in wrap_text("• " + note, d.reg, 2.7, PAGE_W - 2 * MARGIN)[:1]:
                d.text((MARGIN, y2), ln, 2.7, d.reg, GRAY)
                y2 += 4.6

    d.show_page()


# ============================ инструкции ============================

def _instructions_pages(d: PdfDraw, model: ModelDef, meas, params,
                        machine_key: str, draft: DraftResult):
    sections = build_instructions(model, meas, params, machine_key, draft)
    size = 3.1
    lead = 4.7
    x_text = MARGIN + 2
    max_w = CELL_W - 4
    instr_page = [0]

    y = [MARGIN + 2]

    def new_page():
        d.show_page()
        instr_page[0] += 1
        y[0] = MARGIN + 2

    def need(h):
        return (y[0] + h) > (PAGE_H - MARGIN - 4)

    def heading(text, size_mm, color):
        if need(size_mm + 6):
            new_page()
        d.text((MARGIN, y[0]), text, size_mm, d.bold, color)
        y[0] += size_mm + 2.8

    def para(text, font=None, indent=0.0, color=TEXT_COLOR):
        font = font or d.reg
        for line in wrap_text(text, font, size, max_w - indent):
            if need(lead):
                new_page()
            d.text((x_text + indent, y[0]), line, size, font, color)
            y[0] += lead
        y[0] += 1.4

    def page_footer():
        d.text((PAGE_W - MARGIN, PAGE_H - MARGIN + 9.5),
               "Инструкция · стр. %d" % (instr_page[0] + 1), 2.5, d.reg, GRAY,
               align="right")

    heading("ИНСТРУКЦИЯ ПО ШИТЬЮ: " + model.title.upper(), 5.0, BLUE)
    heading("Прочитайте раздел «Перед началом» — там советы по вашей машине.",
            3.0, GRAY)

    for title, blocks in sections:
        if title:
            heading(title.upper(), 4.2, BLUE)
        for b in blocks:
            if b[0] == "h":
                heading(b[1], 3.6, TEXT_COLOR)
            elif b[0] == "p":
                para(b[1])
            elif b[0] == "step":
                _, num, ttl, body = b
                if need(lead * 2 + 4):
                    new_page()
                d.circle((MARGIN + 2.2, y[0] - 0.8), 2.3, BLUE, 0.3,
                         fill=HexColor("#dbeafe"))
                d.text((MARGIN + 2.2, y[0] - 0.7), str(num), 2.5, d.bold,
                       BLUE, align="center")
                d.text((x_text + 5.5, y[0]), ttl, 3.2, d.bold)
                y[0] += lead + 1.2
                para(body, indent=5.5)
                y[0] += 1.6
            elif b[0] == "tip":
                for line in wrap_text("СОВЕТ: " + b[1], d.reg, size, max_w - 6):
                    if need(lead):
                        new_page()
                    d.text((x_text + 3, y[0]), line, size, d.reg,
                           HexColor("#15803d"))
                    y[0] += lead
                y[0] += 1.2
            elif b[0] == "warn":
                for line in wrap_text("ВАЖНО: " + b[1], d.bold, size, max_w - 6):
                    if need(lead):
                        new_page()
                    d.text((x_text + 3, y[0]), line, size, d.bold,
                           HexColor("#b91c1c"))
                    y[0] += lead
                y[0] += 1.2

    page_footer()
    d.show_page()


# ============================ главный экспорт ============================

def export_pdf(path: str, model: ModelDef, meas: Dict[str, float],
               params: Dict[str, object], machine_key: str,
               draft: DraftResult, size_label: str = "",
               include_instructions: bool = True) -> int:
    """Собирает PDF-файл. Возвращает количество страниц."""
    d = PdfDraw(path)

    total_pattern = sum(_piece_page_count(p) for p in draft.pieces)

    _title_page(d, model, meas, params, draft, machine_key, size_label)

    counter = [0]
    for piece in draft.pieces:
        _piece_pages(d, piece, model.title, counter, total_pattern)

    if include_instructions:
        _instructions_pages(d, model, meas, params, machine_key, draft)

    d.save()
    return d.page_no
