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

    # регрессия v1.0.1: полный прогон кнопок «Экспорт PDF» и
    # «Сохранить проект» с подменёнными файловыми диалогами
    # (в v1.0.0 здесь падал NameError: save_settings is not defined)
    test_export_and_save(wiz)

    # v1.2.0: наволочка — ветка «home» мастера (кнопки подушек вместо
    # типовых размеров одежды) + полный проход до экспорта PDF
    test_pillowcase_wizard(root)

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


def test_export_and_save(wiz):
    """Нажатие «Экспорт PDF (A4)» и «Сохранить проект» до конца:
    файловые диалоги и messagebox подменяются, проверяется, что PDF и
    .sewproj реально создаются и ничего не падает (регрессия v1.0.0,
    когда export_pdf_action завершался NameError)."""
    import gui.wizard as W

    pdf_path = os.path.join(OUT, "regress_export.pdf")
    proj_path = os.path.join(OUT, "regress_project.sewproj")

    def fake_asksaveasfilename(**kw):
        title = kw.get("title", "")
        if title.startswith("Экспорт"):
            return pdf_path
        if title.startswith("Сохранить проект"):
            return proj_path
        return ""

    orig_ask = W.filedialog.asksaveasfilename
    orig_showinfo = W.messagebox.showinfo
    orig_askyesno = W.messagebox.askyesno
    W.filedialog.asksaveasfilename = fake_asksaveasfilename
    W.messagebox.showinfo = lambda *a, **kw: None
    W.messagebox.askyesno = lambda *a, **kw: False
    try:
        wiz.export_pdf_action()
        wiz.save_project_action()
    finally:
        W.filedialog.asksaveasfilename = orig_ask
        W.messagebox.showinfo = orig_showinfo
        W.messagebox.askyesno = orig_askyesno

    assert os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 20000, \
        "PDF не создан кнопкой экспорта"
    assert os.path.exists(proj_path), "проект не сохранён кнопкой"
    print("EXPORT/SAVE REGRESSION OK: %s (%d КБ), %s" % (
        pdf_path, os.path.getsize(pdf_path) // 1024, proj_path))


def _first_model():
    from core.models import MODELS
    return MODELS[0]


def test_pillowcase_wizard(root):
    """Полный проход мастера для наволочки (ветка «home»):
    кнопка пресета подушки, шаг мерок без «типовых размеров»,
    параметры, результат и экспорт PDF."""
    from gui.wizard import Wizard
    from core.models import MODELS_BY_ID

    wiz = Wizard(root)
    wiz.update_idletasks()
    time.sleep(0.3)
    wiz.update()

    pc = MODELS_BY_ID["pillowcase"]
    wiz.pick_model(pc)
    wiz.update()
    time.sleep(0.3)
    grab(wiz, "08_wizard_pillow_measurements.png")

    # кнопка «50 × 70 (евро)» — должна заполнить поля размеров
    wiz._fill_pillow(50.0, 70.0)
    assert wiz._meas_vars["pillow_w"].get() == "50"
    assert wiz._meas_vars["pillow_l"].get() == "70"
    assert wiz.validate_measurements(), "мерки подушки не прошли валидацию"
    assert "50×70" in wiz.state.size_label

    wiz.step = 2
    wiz.render_step()
    wiz.update()
    wiz.step = 3
    wiz.render_step()
    wiz.update()
    time.sleep(0.2)
    grab(wiz, "09_wizard_pillow_params.png")

    wiz.collect_params()
    wiz.rebuild_draft()
    assert wiz.state.draft is not None
    piece = wiz.state.draft.pieces[0]
    x0, y0, x1, y1 = piece.bbox(True)
    assert abs((x1 - x0) - 53.0) < 0.1, "ширина кроя наволочки неверна"
    assert abs((y1 - y0) - 164.0) < 0.1, "длина кроя наволочки неверна"

    wiz.step = 4
    wiz.render_step()
    time.sleep(0.5)
    wiz.update()
    time.sleep(0.4)
    wiz.preview.fit()
    wiz.update()
    time.sleep(0.3)
    grab(wiz, "10_wizard_pillow_result.png")

    # экспорт PDF из результата (диалог подменён)
    import gui.wizard as W
    pdf_path = os.path.join(OUT, "regress_pillowcase.pdf")

    def fake_asksaveasfilename(**kw):
        return pdf_path if kw.get("title", "").startswith("Экспорт") else ""

    orig_ask = W.filedialog.asksaveasfilename
    orig_askyesno = W.messagebox.askyesno
    W.filedialog.asksaveasfilename = fake_asksaveasfilename
    W.messagebox.askyesno = lambda *a, **kw: False
    try:
        wiz.export_pdf_action()
    finally:
        W.filedialog.asksaveasfilename = orig_ask
        W.messagebox.askyesno = orig_askyesno
    assert os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 20000, \
        "PDF наволочки не создан"
    print("PILLOWCASE WIZARD OK: %s (%d КБ), крой %.1f x %.1f"
          % (pdf_path, os.path.getsize(pdf_path) // 1024,
             x1 - x0, y1 - y0))
    wiz.destroy()


if __name__ == "__main__":
    run()
