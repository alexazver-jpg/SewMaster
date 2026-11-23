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


def main():
    results = []
    for model in MODELS:
        meas = model.default_measurements()
        params = model.default_params()
        draft = model.build(meas, params)
        check_draft(model, draft)

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
