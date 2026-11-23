# -*- coding: utf-8 -*-
"""Общие стили и утилиты GUI."""
from __future__ import annotations

import os
import subprocess
import sys

# палитра (совпадает с PDF)
BLUE = "#1d4ed8"
BLUE_LIGHT = "#dbeafe"
BLUE_BG = "#eff6ff"
DARK = "#111827"
GRAY = "#6b7280"
GRID = "#d1d5db"
RED = "#dc2626"
GREEN = "#15803d"
PURPLE = "#7c3aed"
ORANGE = "#b45309"
BG = "#f8fafc"
GRID_LIGHT = "#e5e7eb"


def open_file(path: str) -> None:
    """Открыть файл в системном приложении (PDF и т.п.)."""
    if not path or not os.path.exists(path):
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError:
        pass


def fmt_cm(v: float) -> str:
    return ("%g" % round(v, 1)).replace(".", ",")


_font_family = None


def ui_family() -> str:
    """Семейство шрифта интерфейса с поддержкой кириллицы.

    На Windows — Segoe UI (есть на Win 7-11), далее запасные варианты.
    """
    global _font_family
    if _font_family is None:
        try:
            import tkinter as tk
            import tkinter.font as tkfont
            tmp = tk.Tk()
            tmp.withdraw()
            avail = set(tkfont.families())
            for f in ("Segoe UI", "Verdana", "Tahoma", "DejaVu Sans"):
                if f in avail:
                    _font_family = f
                    break
            else:
                _font_family = tkfont.nametofont(
                    "TkDefaultFont").actual("family")
            tmp.destroy()
        except Exception:
            _font_family = "Segoe UI"
    return _font_family
