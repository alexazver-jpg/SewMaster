# -*- coding: utf-8 -*-
"""Дымовой тест: построение всех моделей, генерация PDF, базовые проверки."""
from __future__ import annotations

import math
import os
import sys

# Windows-консоль может использовать cp1251/cp1252 — переключаем на UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.models import MODELS
from core.pdfout import export_pdf
from core.instructions import build_instructions, instructions_to_text


def check_gui_imports():
    """Регрессия v1.0.1: в v1.0.0 кнопка «Экспорт PDF» падала с
    NameError: name 'save_settings' is not defined — функция не была
    импортирована в gui/wizard.py. Проверяем, что все имена, которые
    использует мастер, реально есть в его пространстве имён."""
    import gui.wizard as wizard_mod
    for name in ("save_settings", "load_settings", "save_project",
                 "remember_recent", "Project", "export_pdf", "MACHINES"):
        assert hasattr(wizard_mod, name), \
            "gui/wizard.py: имя %r не импортировано (NameError при нажатии кнопки)" % name

OUT = os.environ.get("SEWMASTER_TEST_OUT",
                     os.path.join(os.path.dirname(__file__), "..", "..", "test_pdfs"))
os.makedirs(OUT, exist_ok=True)


def check_draft(model, draft):
    assert draft.pieces, "нет деталей"
    for piece in draft.pieces:
        x0, y0, x1, y1 = piece.bbox(True)
        assert x1 - x0 > 5 and y1 - y0 > 5, \
            "деталь %s подозрительно мала: %g x %g" % (piece.name, x1 - x0, y1 - y0)
        cut = piece.cut_poly
        assert len(cut) >= 10, "слишком мало точек в контуре кроя"
        # линия кроя должна быть ВНЕ линии шва (площадь больше)
        from core.geom import polygon_area
        seam = piece.contour.points(20) + [piece.contour.start]
        assert abs(polygon_area(cut)) >= abs(polygon_area(seam)), \
            "контур кроя не охватывает линию шва: " + piece.name


def check_wearability(model, draft, meas):
    """Регрессия v1.1.0: изделия должны собираться и надеваться.
    В v1.0.0 боксёры имели отверстие для ноги 8 см (бедро ~62),
    рукав футболки не совпадал с проймой, горловина не проходила голову."""
    from core.geom import dist

    def slen(piece, idx):
        g = piece.contour.seg_groups(48)
        seg = g[idx]
        return sum(dist(seg[j], seg[j + 1]) for j in range(len(seg) - 1))

    mid = model.model_id
    hips = float(meas.get("hips") or 0)
    thigh = float(meas.get("thigh") or hips * 0.62)

    if mid in ("boxers", "shorts"):
        opening = 2.0 * slen(draft.pieces[0], 2)   # перед + зад
        assert opening >= thigh + 1.0, \
            "%s: отверстие для ноги %.1f < бедра %.1f" % (mid, opening, thigh)
    if mid in ("briefs", "boxers", "shorts", "skirt_sun"):
        # пояс/кольцо должны проходить через бёдра
        if mid == "skirt_sun":
            r = [v for n, v in draft.checks if n.startswith("Радиус линии пояса")][0]
            ring = 2 * math.pi * r
        else:
            ring = 2.0 * (slen(draft.pieces[0], 0) + slen(draft.pieces[1], 0))
        assert ring >= hips + 1.0, \
            "%s: пояс %.1f не проходит через бёдра %.1f" % (mid, ring, hips)
    if mid in ("tank", "tee", "longsleeve"):
        neck_open = slen(draft.pieces[0], 0) + slen(draft.pieces[1], 0)
        neck = float(meas.get("neck") or 36)
        assert neck_open >= neck * 0.55, \
            "%s: горловина %.1f слишком мала для Ош %.0f" % (mid, neck_open, neck)
    if mid in ("tee", "longsleeve"):
        # окат рукава == пройме-кольцу (assert уже в drafts, но продублируем)
        ring = slen(draft.pieces[0], 2) + slen(draft.pieces[1], 2)
        cap = slen(draft.pieces[2], 0)
        assert abs(cap - ring) <= 1.5, \
            "%s: окат %.1f != пройма-кольцо %.1f" % (mid, cap, ring)
        arm = float(meas.get("arm") or 30)
        assert cap >= arm + 4.0, \
            "%s: труба рукава %.1f уже плеча %.1f" % (mid, cap, arm)


def main():
    check_gui_imports()
    results = []
    for model in MODELS:
        meas = model.default_measurements()
        params = model.default_params()
        draft = model.build(meas, params)
        check_draft(model, draft)
        check_wearability(model, draft, meas)

        # с нестандартными мерками
        meas2 = dict(meas)
        for k in meas2:
            meas2[k] = meas2[k] * 1.25
        params2 = dict(params)
        for pf in model.params:
            if not pf.choices:
                params2[pf.key] = pf.default
        draft2 = model.build(meas2, params2)
        check_draft(model, draft2)
        check_wearability(model, draft2, meas2)

        # инструкция
        sections = build_instructions(model, meas, params, "straight", draft)
        text = instructions_to_text(sections)
        assert "ШАГ" in text and len(text) > 1500, "инструкция подозрительно короткая"
        for mk in ("zigzag", "overlock", "cover"):
            s2 = build_instructions(model, meas, params, mk, draft)
            t2 = instructions_to_text(s2)
            assert len(t2) > 1500, "инструкция для машины %s пустая" % mk

        # PDF
        fname = os.path.join(OUT, "SewMaster_%s_test.pdf" % model.model_id)
        pages = export_pdf(fname, model, meas, params, "zigzag", draft,
                           size_label="46 (тест)", include_instructions=True)
        assert os.path.exists(fname) and os.path.getsize(fname) > 20000, "PDF пустой"
        results.append((model.model_id, pages, round(os.path.getsize(fname) / 1024.0, 1)))

    print("%-10s %-8s %-10s" % ("модель", "страниц", "КБ"))
    for r in results:
        print("%-10s %-8s %-10s" % r)
    print("SMOKE OK")


if __name__ == "__main__":
    main()
