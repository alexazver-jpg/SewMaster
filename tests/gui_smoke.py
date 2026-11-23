# -*- coding: utf-8 -*-
"""Дымовой тест GUI под xvfb: открытие окон мастера + скриншоты."""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tkinter as tk

OUT = os.environ.get("SEWMASTER_SHOT_DIR", "/tmp/gui_shots")
os.makedirs(OUT, exist_ok=True)


def grab(win, name):
    """Снимок ТОЛЬКО окна (кроп по геометрии виджета)."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(xdisplay=os.environ.get("DISPLAY"))
        x = win.winfo_rootx() - win.winfo_x()
        y = win.winfo_rooty() - win.winfo_y()
        w = win.winfo_width()
        h = win.winfo_height()
        # окно может быть смещено; берём фактические экранные координаты
        rx, ry = win.winfo_rootx(), win.winfo_rooty()
        img = img.crop((max(0, rx - 4), max(0, ry - 30),
                        min(img.width, rx + w + 4),
                        min(img.height, ry - 30 + h + 34)))
        img.save(os.path.join(OUT, name))
        print("снимок:", name, img.size)
    except Exception as e:
        print("скриншот недоступен:", e)


def run():
    from gui.windows import MainWindow
    from gui.wizard import Wizard, WizardState

    root = MainWindow()
    root.update_idletasks()
    time.sleep(0.4)
    root.update()
    grab(root, "01_main.png")

    wiz = Wizard(root)
    wiz.update_idletasks()
    time.sleep(0.4)
    wiz.update()
    grab(wiz, "02_wizard_model.png")

    # выбор модели -> мерки
    wiz.pick_model(wiz.state.__class__ and _first_model())
    wiz.update()
    time.sleep(0.3)
    grab(wiz, "03_wizard_measurements.png")

    # машина
    wiz.step = 2
    wiz.render_step()
    wiz.update()
    time.sleep(0.3)
    grab(wiz, "04_wizard_machine.png")

    # параметры
    wiz.step = 3
    wiz.render_step()
    wiz.update()
    time.sleep(0.3)
    grab(wiz, "05_wizard_params.png")

    # результат (предпросмотр)
    wiz.collect_params()
    wiz.rebuild_draft()
    wiz.step = 4
    wiz.render_step()
    time.sleep(0.5)
    wiz.update()
    time.sleep(0.5)
    wiz.preview.fit()
    wiz.update()
    time.sleep(0.5)
    grab(wiz, "06_wizard_result.png")

    # окно инструкции
    from gui import windows as W
    from core.instructions import build_instructions
    st = wiz.state
    sections = build_instructions(st.model, st.measurements, st.params,
                                  st.machine_key, st.draft)
    iw = W.show_instructions(root, st, sections)
    iw.update()
    time.sleep(0.3)
    grab(iw, "07_instructions.png")

    wiz.destroy()
    iw.destroy()
    root.destroy()
    print("GUI SMOKE OK")


def _first_model():
    from core.models import MODELS
    return MODELS[0]


if __name__ == "__main__":
    run()
