# -*- coding: utf-8 -*-
"""Панель предпросмотра выкройки: масштабирование, панорама, переключатели."""
from __future__ import annotations

import math
import tkinter as tk
from typing import List, Optional, Tuple

from core.piece import PatternPiece
from .theme import (BG, BLUE, DARK, GRAY, GRID, GREEN, ORANGE, PURPLE, RED,
                    ui_family)


class PreviewPanel(tk.Frame):
    """Canvas с выкройкой: зум колесом, панорама мышью."""

    def __init__(self, master, pieces_provider, status_var=None, **kw):
        tk.Frame.__init__(self, master, bg=BG, **kw)
        self.pieces_provider = pieces_provider   # callable -> List[PatternPiece]
        self.status_var = status_var
        self.show_seam = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=True)
        self.show_marks = tk.BooleanVar(value=True)

        self.scale = 6.0          # пикселей на см
        self.view_x = 0.0         # см, левый верхний угол вида
        self.view_y = 0.0
        self._drag = None         # type: Optional[Tuple[int, int, float, float]]

        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0,
                                cursor="fleur")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Configure>", self._on_configure)
        self._fitted = False
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", self._on_wheel)
        self.canvas.bind("<Button-5>", self._on_wheel)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", lambda e: self._drag_stop())

        # переключатели поверх холста
        bar = tk.Frame(self.canvas, bg="white")
        for text, var in (("линия шва", self.show_seam),
                          ("сетка 10 см", self.show_grid),
                          ("метки", self.show_marks)):
            tk.Checkbutton(bar, text=text, variable=var, command=self.redraw,
                           bg="white", fg=DARK, activebackground="white",
                           font=(ui_family(), 9)).pack(side=tk.LEFT, padx=6)
        tk.Label(bar, text="  колесо — зум, тяга мышью — движение",
                 bg="white", fg=GRAY, font=(ui_family(), 8)).pack(side=tk.LEFT)
        bar.place(x=8, y=6)

    def _on_configure(self, event):
        if not self._fitted and event.width > 10:
            self._fitted = True
            self.after_idle(self.fit)
        self.redraw()

    # ---- трансформация ---------------------------------------------------
    def _w2s(self, p) -> Tuple[float, float]:
        return ((p[0] - self.view_x) * self.scale,
                (p[1] - self.view_y) * self.scale)

    def _layout(self, pieces):
        """Раскладка деталей в ряд с зазором 4 см (единая для fit и redraw)."""
        laid = []
        x_cursor = 0.0
        for p in pieces:
            bb = p.bbox(True)
            laid.append(p.placed(x_cursor - bb[0], -bb[1]))
            x_cursor += (bb[2] - bb[0]) + 4.0
        return laid

    def fit(self):
        pieces = self.pieces_provider()
        if not pieces:
            return
        laid = self._layout(pieces)
        xs0, ys0, xs1, ys1 = [], [], [], []
        for p in laid:
            x0, y0, x1, y1 = p.bbox(True)
            xs0.append(x0); ys0.append(y0); xs1.append(x1); ys1.append(y1)
        x0, y0, x1, y1 = min(xs0), min(ys0), max(xs1), max(ys1)
        w = self.canvas.winfo_width() or 600
        h = self.canvas.winfo_height() or 400
        pad = 3.0
        sx = (w - 70) / max(x1 - x0 + 2 * pad, 1e-6)
        sy = (h - 70) / max(y1 - y0 + 2 * pad, 1e-6)
        self.scale = max(1.0, min(sx, sy, 30.0))
        self.view_x = x0 - pad - (((w - 40) / self.scale - (x1 - x0 + 2 * pad)) / 2)
        self.view_y = y0 - pad - (((h - 40) / self.scale - (y1 - y0 + 2 * pad)) / 2)
        self.redraw()

    # ---- события ----------------------------------------------------------
    def _on_wheel(self, event):
        if getattr(event, "delta", None):
            factor = 1.1 if event.delta > 0 else 1 / 1.1
        elif event.num == 4:
            factor = 1.1
        else:
            factor = 1 / 1.1
        # зум к позиции курсора
        cx = self.canvas.canvasx(event.x) / self.scale + self.view_x
        cy = self.canvas.canvasy(event.y) / self.scale + self.view_y
        self.scale = max(1.0, min(self.scale * factor, 60.0))
        self.view_x = cx - event.x / self.scale
        self.view_y = cy - event.y / self.scale
        self.redraw()

    def _on_press(self, event):
        self._drag = (event.x, event.y, self.view_x, self.view_y)

    def _on_motion(self, event):
        if not self._drag:
            return
        x0, y0, vx, vy = self._drag
        self.view_x = vx - (event.x - x0) / self.scale
        self.view_y = vy - (event.y - y0) / self.scale
        self.redraw()

    def _drag_stop(self):
        self._drag = None

    # ---- отрисовка ---------------------------------------------------------
    def redraw(self):
        c = self.canvas
        c.delete("all")
        pieces = self.pieces_provider()
        if not pieces:
            return
        laid = self._layout(pieces)

        all_x0, all_y0, all_x1, all_y1 = 1e9, 1e9, -1e9, -1e9
        for p in laid:
            x0, y0, x1, y1 = p.bbox(True)
            all_x0 = min(all_x0, x0); all_y0 = min(all_y0, y0)
            all_x1 = max(all_x1, x1); all_y1 = max(all_y1, y1)

        # сетка 10 см
        if self.show_grid.get():
            step = 10.0
            k = math.floor(all_x0 / step) * step
            while k <= all_x1:
                a, b = self._w2s((k, all_y0)), self._w2s((k, all_y1))
                c.create_line(a[0], a[1], b[0], b[1], fill=GRID, width=1,
                              dash=(2, 3))
                k += step
            k = math.floor(all_y0 / step) * step
            while k <= all_y1:
                a, b = self._w2s((all_x0, k)), self._w2s((all_x1, k))
                c.create_line(a[0], a[1], b[0], b[1], fill=GRID, width=1,
                              dash=(2, 3))
                k += step

        for piece in laid:
            self._draw_piece(c, piece)

        if self.status_var is not None:
            self.status_var.set(
                "Масштаб: 1 см = %.1f px · детали: %d"
                % (self.scale, len(laid)))

    def _draw_piece(self, c, piece: PatternPiece):
        cut = [self._w2s(p) for p in piece.cut_poly]
        if len(cut) > 2:
            c.create_polygon(cut, fill="#eef2ff", outline=DARK, width=2)
        if self.show_seam.get():
            seam = [self._w2s(p) for p in piece.contour.points(20)]
            seam.append(self._w2s(piece.contour.start))
            c.create_line(seam, fill=RED, width=1, dash=(4, 3))

        if self.show_marks.get():
            for (a, b) in piece.folds:
                c.create_line(self._w2s(a), self._w2s(b), fill=PURPLE,
                              width=2, dash=(7, 3, 1, 3))
            if piece.grain:
                c.create_line(self._w2s(piece.grain[0]),
                              self._w2s(piece.grain[1]), fill=GREEN, width=2,
                              arrow=tk.BOTH)
            for n in piece.notches:
                ang = math.radians(n.angle_deg)
                d = (math.cos(ang), math.sin(ang))
                allow = piece.allowance or 1.0
                p1 = (n.pt[0] + d[0] * 0.35, n.pt[1] + d[1] * 0.35)
                p2 = (n.pt[0] - d[0] * (allow + 0.25),
                      n.pt[1] - d[1] * (allow + 0.25))
                c.create_line(self._w2s(p1), self._w2s(p2), fill=ORANGE,
                              width=2)

        # подпись детали под деталью
        bb = piece.bbox(True)
        cx = (bb[0] + bb[2]) / 2.0
        ty = bb[3] + 1.2
        c.create_text(self._w2s((cx, ty)),
                      text="%s · %s" % (piece.name, piece.size_text()),
                      fill=DARK, font=(ui_family(), 9, "bold"))
        c.create_text(self._w2s((cx, ty + 1.6)),
                      text=piece.cut_note, fill=GRAY,
                      font=(ui_family(), 8))
        # метки-надписи внутри детали
        if self.show_marks.get():
            for lbl in piece.labels:
                for i, line in enumerate(lbl.lines):
                    c.create_text(self._w2s((lbl.pt[0], lbl.pt[1] + i * 1.8)),
                                  text=line, fill=DARK,
                                  font=(ui_family(), 9, "bold"))
