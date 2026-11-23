# -*- coding: utf-8 -*-
"""Мастер создания выкройки: модель → мерки → машина → параметры → результат."""
from __future__ import annotations

import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from core import catalog as catalog_mod
from core.instructions import build_instructions, instructions_to_text
from core.models import (MODELS, ModelDef, get_model, size_defaults)
from core.pdfout import export_pdf
from core.piece import DraftResult
from core.sewing import MACHINES
from core.storage import (PROJECT_EXT, Project, remember_recent,
                          save_project, load_settings, save_settings)
from .preview import PreviewPanel
from .theme import (BG, BLUE, BLUE_BG, BLUE_LIGHT, DARK, GRAY, GREEN,
                    GRID_LIGHT, ui_family)
from . import windows


class WizardState(object):
    def __init__(self):
        self.model = None          # type: Optional[ModelDef]
        self.measurements = {}     # type: Dict[str, float]
        self.params = {}           # type: Dict[str, object]
        self.machine_key = "zigzag"
        self.size_label = ""
        self.audience = tk.StringVar()
        self.project_path = None   # type: Optional[str]
        self.draft = None          # type: Optional[DraftResult]


class Wizard(tk.Toplevel):
    STEPS = ["Модель", "Мерки", "Швейная машина", "Параметры", "Результат"]

    def __init__(self, master, state: Optional[WizardState] = None,
                 start_step: int = 0):
        tk.Toplevel.__init__(self, master)
        self.title("SewMaster — новая выкройка")
        self.geometry("1060x760")
        self.minsize(940, 640)
        self.state = state or WizardState()
        self.step = start_step
        self._meas_vars = {}   # type: Dict[str, tk.StringVar]
        self._param_vars = {}  # type: Dict[str, tk.Variable]

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill=tk.BOTH, expand=True)

        # нижняя панель навигации
        nav = tk.Frame(self, bg="white")
        nav.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(nav, bg=GRID_LIGHT, height=1).pack(fill=tk.X)
        self.btn_back = tk.Button(nav, text="← Назад", command=self.go_back,
                                  font=(ui_family(), 10), relief=tk.FLAT,
                                  bg="white", fg=DARK, padx=14, pady=6)
        self.btn_back.pack(side=tk.LEFT, padx=10, pady=10)
        self.btn_next = tk.Button(nav, text="Далее →", command=self.go_next,
                                  font=(ui_family(), 10, "bold"), relief=tk.FLAT,
                                  bg=BLUE, fg="white", padx=18, pady=6)
        self.btn_next.pack(side=tk.RIGHT, padx=10, pady=10)

        self.progress = tk.Label(nav, text="", bg="white", fg=GRAY,
                                 font=(ui_family(), 9))
        self.progress.pack(side=tk.RIGHT, padx=12)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.render_step()
        windows.center_window(self)

    # ==================== навигация ====================
    def go_back(self):
        if self.step > 0:
            self.step -= 1
            self.render_step()

    def go_next(self):
        if self.step == 1 and not self.validate_measurements():
            return
        if self.step == 3:
            self.collect_params()
            self.rebuild_draft()
        if self.step < len(self.STEPS) - 1:
            self.step += 1
            self.render_step()

    def render_step(self):
        for w in self.container.winfo_children():
            w.destroy()
        self.progress.config(text="Шаг %d из %d: %s"
                             % (self.step + 1, len(self.STEPS),
                                self.STEPS[self.step]))
        self.btn_back.config(state=tk.NORMAL if self.step > 0 else tk.DISABLED)
        self.btn_next.config(
            text="Готово ✓" if self.step == len(self.STEPS) - 1 else "Далее →",
            state=tk.DISABLED if self.step == len(self.STEPS) - 1 else tk.NORMAL)

        if self.step == 0:
            self._page_model()
        elif self.step == 1:
            self._page_measurements()
        elif self.step == 2:
            self._page_machine()
        elif self.step == 3:
            self._page_params()
        else:
            self._page_result()

    # ==================== шаг 1: модель ====================
    def _page_model(self):
        f = tk.Frame(self.container, bg=BG)
        f.pack(fill=tk.BOTH, expand=True)
        windows.page_header(f, "Выберите модель",
                            "Что будем шить? В первой версии — бельё и лёгкий верх. "
                            "Позже модели можно докачать из онлайн-каталога.")

        wrap = tk.Frame(f, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=24, pady=8)

        models = list(MODELS) + catalog_mod.list_local_catalog_models()
        for i, model in enumerate(models):
            card = tk.Frame(wrap, bg="white", highlightthickness=1,
                            highlightbackground=GRID_LIGHT)
            card.grid(row=i // 4, column=i % 4, padx=8, pady=8,
                      sticky="nsew")
            wrap.grid_columnconfigure(i % 4, weight=1)

            # мини-превью выкройки
            try:
                draft = model.build(model.default_measurements(),
                                    model.default_params())
                thumb = tk.Canvas(card, width=190, height=150, bg="white",
                                  highlightthickness=0)
                thumb.pack(padx=8, pady=(8, 2))
                windows.draw_thumb(thumb, draft)
            except Exception:
                thumb = tk.Canvas(card, width=190, height=150, bg="white",
                                  highlightthickness=0)
                thumb.pack(padx=8, pady=(8, 2))

            tk.Label(card, text=model.title, bg="white", fg=DARK, height=2,
                     font=(ui_family(), 11, "bold"), wraplength=180).pack()
            tk.Label(card, text=model.description[:110] + "…", bg="white",
                     fg=GRAY, font=(ui_family(), 8), wraplength=180,
                     justify=tk.LEFT, height=4).pack(padx=6)
            if model.source == "catalog":
                tk.Label(card, text="из онлайн-каталога", bg=BLUE_LIGHT,
                         fg=BLUE, font=(ui_family(), 8)).pack(pady=(0, 4))
            btn = tk.Button(card, text="Выбрать", relief=tk.FLAT, bg=BLUE,
                            fg="white", font=(ui_family(), 9, "bold"),
                            padx=10, pady=3,
                            command=lambda m=model: self.pick_model(m))
            btn.pack(pady=(2, 10))

    def pick_model(self, model: ModelDef):
        self.state.model = model
        self.state.measurements = model.default_measurements()
        self.state.params = model.default_params()
        self.state.audience.set(model.audience if model.audience != "uni"
                                else "women")
        self.step = 1
        self.render_step()

    # ==================== шаг 2: мерки ====================
    def _page_measurements(self):
        model = self.state.model
        f = tk.Frame(self.container, bg=BG)
        f.pack(fill=tk.BOTH, expand=True)
        windows.page_header(f, "Мерки — %s" % model.title,
                            "Измерьте себя сантиметровой лентой. "
                            "Нажмите «Заполнить по стандартному размеру», "
                            "а затем поправьте значения под себя.")

        body = tk.Frame(f, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=8)

        left = tk.Frame(body, bg="white", highlightthickness=1,
                        highlightbackground=GRID_LIGHT)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        body.grid_columnconfigure(0, weight=3)
        body.grid_rowconfigure(0, weight=1)

        tk.Label(left, text="Мерки, см", bg="white", fg=DARK,
                 font=(ui_family(), 11, "bold")).grid(row=0, column=0,
                                                     columnspan=2, sticky="w",
                                                     padx=14, pady=(10, 4))
        self._meas_vars.clear()
        for i, field in enumerate(model.measurements):
            var = tk.StringVar(value=("%g" % self.state.measurements.get(
                field.key, field.typical)))
            self._meas_vars[field.key] = var
            row = i + 1
            req = "" if field.required else " (не обязательно)"
            tk.Label(left, text=field.label + req, bg="white", fg=DARK,
                     font=(ui_family(), 10), anchor="w",
                     justify=tk.LEFT).grid(row=row, column=0, sticky="w",
                                           padx=(14, 4), pady=4)
            e = tk.Entry(left, textvariable=var, width=10, font=(ui_family(), 11),
                         relief=tk.SOLID, bd=1)
            e.grid(row=row, column=1, sticky="w", padx=(4, 14), pady=4)
            hint = tk.Label(left, text=field.hint, bg="white", fg=GRAY,
                            font=(ui_family(), 8), wraplength=480,
                            justify=tk.LEFT, anchor="w")
            hint.grid(row=row, column=2, sticky="w", padx=(0, 14), pady=4)
            left.grid_columnconfigure(2, weight=1)
            left.grid_columnconfigure(0, weight=1)

        # правая колонка: стандартные размеры
        right = tk.Frame(body, bg="white", highlightthickness=1,
                         highlightbackground=GRID_LIGHT)
        right.grid(row=0, column=1, sticky="nsew")
        body.grid_columnconfigure(1, weight=2)

        tk.Label(right, text="Подсказка", bg="white", fg=DARK,
                 font=(ui_family(), 11, "bold")).pack(pady=(10, 4), padx=12,
                                                      anchor="w")
        tk.Label(right, text=("Как измерять:\n"
                              "• встаньте ровно, лента — параллельно полу;\n"
                              "• лента прилегает плотно, но не стягивает;\n"
                              "• запишите результат в сантиметрах.\n\n"
                              "Мерки можно сохранить в проект и потом "
                              "использовать снова."),
                 bg="white", fg=GRAY, font=(ui_family(), 9), justify=tk.LEFT,
                 wraplength=260).pack(padx=12, anchor="w")

        tk.Label(right, text="Тип фигуры", bg="white", fg=DARK,
                 font=(ui_family(), 10, "bold")).pack(pady=(14, 2), padx=12,
                                                      anchor="w")
        aud = ttk.Combobox(right, textvariable=self.state.audience,
                           values=["женская", "мужская"], state="readonly",
                           width=18)
        aud.pack(padx=12, anchor="w")

        tk.Label(right, text="Стандартный размер", bg="white", fg=DARK,
                 font=(ui_family(), 10, "bold")).pack(pady=(14, 2), padx=12,
                                                      anchor="w")
        self.size_combo = ttk.Combobox(
            right, values=[str(s) for s in range(42, 63, 2)], width=18,
            state="readonly")
        self.size_combo.set("46")
        self.size_combo.pack(padx=12, anchor="w")
        tk.Button(right, text="Заполнить по размеру", relief=tk.FLAT, bg=BLUE,
                  fg="white", font=(ui_family(), 9, "bold"), padx=10, pady=4,
                  command=self.fill_from_size).pack(pady=10, padx=12,
                                                    anchor="w")

        info = tk.Label(right, text="Типовые мерки — усреднённые. "
                          "Обязательно проверьте свои значения!",
                        bg=BLUE_BG, fg=DARK, font=(ui_family(), 8),
                        wraplength=240, justify=tk.LEFT)
        info.pack(padx=12, pady=(4, 12), anchor="w")

    def fill_from_size(self):
        model = self.state.model
        try:
            size = int(self.size_combo.get())
        except ValueError:
            return
        audience = "men" if self.state.audience.get() == "мужская" else "women"
        defaults = size_defaults(audience, size)
        self.state.size_label = "размер %d" % size
        for key, var in self._meas_vars.items():
            if key in defaults:
                var.set("%g" % defaults[key])
            else:
                field = next(f for f in model.measurements if f.key == key)
                if audience == "men" and key in ("rise"):
                    var.set("27")
                else:
                    var.set("%g" % field.typical)

    def validate_measurements(self) -> bool:
        model = self.state.model
        self.state.measurements = {}
        for field in model.measurements:
            raw = self._meas_vars[field.key].get().strip().replace(",", ".")
            if raw == "" and not field.required:
                continue
            try:
                val = float(raw)
            except ValueError:
                messagebox.showwarning("Проверьте мерки",
                                       "Значение «%s» должно быть числом.\n"
                                       "Например: 92" % field.label, parent=self)
                return False
            if field.vmin and val < field.vmin or field.vmax and val > field.vmax:
                messagebox.showwarning(
                    "Проверьте мерки",
                    "«%s» = %g выглядит неправдоподобно.\n"
                    "Допустимый диапазон: от %g до %g см."
                    % (field.label, val, field.vmin, field.vmax), parent=self)
                return False
            self.state.measurements[field.key] = val
        for field in model.measurements:
            if field.required and field.key not in self.state.measurements:
                messagebox.showwarning("Мерки", "Заполните обязательную мерку «%s»."
                                       % field.label, parent=self)
                return False
        return True

    # ==================== шаг 3: машина ====================
    def _page_machine(self):
        f = tk.Frame(self.container, bg=BG)
        f.pack(fill=tk.BOTH, expand=True)
        windows.page_header(f, "Ваша швейная машина",
                            "Программа подстроит инструкцию под доступные швы. "
                            "Нет оверлока — предложим зигзаг или бельевой шов.")

        wrap = tk.Frame(f, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=24, pady=8)
        self._machine_var = tk.StringVar(value=self.state.machine_key)
        for i, (key, m) in enumerate(MACHINES.items()):
            card = tk.Frame(wrap, bg="white", highlightthickness=1,
                            highlightbackground=GRID_LIGHT)
            card.grid(row=0, column=i, padx=8, sticky="nsew")
            wrap.grid_columnconfigure(i, weight=1)
            rb = tk.Radiobutton(card, text=m.title, variable=self._machine_var,
                                value=key, bg="white", fg=DARK,
                                font=(ui_family(), 11, "bold"),
                                activebackground="white", anchor="w")
            rb.pack(padx=10, pady=(12, 4), anchor="w")
            tk.Label(card, text=m.description, bg="white", fg=GRAY,
                     font=(ui_family(), 9), wraplength=200, justify=tk.LEFT,
                     height=5).pack(padx=10, anchor="w")
            tk.Label(card, text="Доступно: " + m.summary(), bg=BLUE_BG,
                     fg=DARK, font=(ui_family(), 8), wraplength=200,
                     justify=tk.LEFT).pack(padx=10, pady=(2, 12), anchor="w")

    # ==================== шаг 4: параметры ====================
    def _page_params(self):
        model = self.state.model
        f = tk.Frame(self.container, bg=BG)
        f.pack(fill=tk.BOTH, expand=True)
        windows.page_header(f, "Параметры — %s" % model.title,
                            "Посадка, резинка и припуски. Если сомневаетесь — "
                            "оставьте значения по умолчанию.")

        body = tk.Frame(f, bg="white", highlightthickness=1,
                        highlightbackground=GRID_LIGHT)
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=8)
        self._param_vars.clear()
        for i, pf in enumerate(model.params):
            current = self.state.params.get(pf.key, pf.default)
            row = i
            tk.Label(body, text=pf.label, bg="white", fg=DARK,
                     font=(ui_family(), 10)).grid(row=row, column=0, sticky="w",
                                                 padx=(14, 4), pady=6)
            if pf.choices:
                var = tk.StringVar(value=str(current))
                cb = ttk.Combobox(body, textvariable=var, state="readonly",
                                  width=22,
                                  values=[c.label for c in pf.choices])
                cb.grid(row=row, column=1, sticky="w", padx=4, pady=6)
                self._param_vars[pf.key] = ("choice", var)
            else:
                var = tk.StringVar(value=str(current))
                sp = tk.Spinbox(body, textvariable=var, from_=pf.vmin,
                                to=pf.vmax, increment=0.5, width=8,
                                font=(ui_family(), 10))
                sp.grid(row=row, column=1, sticky="w", padx=4, pady=6)
                self._param_vars[pf.key] = ("num", var)
            if pf.hint:
                tk.Label(body, text=pf.hint, bg="white", fg=GRAY,
                         font=(ui_family(), 8), wraplength=420,
                         justify=tk.LEFT, anchor="w").grid(
                             row=row, column=2, sticky="w", padx=(4, 14),
                             pady=6)
        body.grid_columnconfigure(2, weight=1)

    def collect_params(self):
        model = self.state.model
        params = {}
        for pf in model.params:
            kind, var = self._param_vars[pf.key]
            if kind == "choice":
                label = var.get()
                val = pf.default
                for c in pf.choices:
                    if c.label == label:
                        val = c.value
                        break
                params[pf.key] = val
            else:
                try:
                    v = float(var.get().replace(",", "."))
                    v = max(pf.vmin, min(pf.vmax, v))
                    params[pf.key] = v
                except ValueError:
                    params[pf.key] = pf.default
        self.state.params = params
        if self._machine_var is not None:
            self.state.machine_key = self._machine_var.get()

    # ==================== шаг 5: результат ====================
    def rebuild_draft(self):
        st = self.state
        if st.model is None:
            return
        st.params = dict(st.model.default_params()) if not st.params else st.params
        st.draft = st.model.build(st.measurements, st.params)

    def _page_result(self):
        st = self.state
        if st.draft is None:
            self.rebuild_draft()
        f = tk.Frame(self.container, bg=BG)
        f.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(f, bg="white")
        header.pack(fill=tk.X)
        inner = tk.Frame(header, bg="white")
        inner.pack(fill=tk.X, padx=24, pady=10)
        tk.Label(inner, text="%s — выкройка готова" % st.model.title,
                 bg="white", fg=DARK, font=(ui_family(), 14, "bold")).pack(
                     side=tk.LEFT)
        tk.Label(inner,
                 text=("Мерки: " + ", ".join(
                     "%g" % v for v in list(st.measurements.values())[:3])
                     + " см · припуск %g см" % st.draft.pieces[0].allowance),
                 bg="white", fg=GRAY, font=(ui_family(), 9)).pack(
                     side=tk.LEFT, padx=12)

        # кнопки действий
        actions = tk.Frame(header, bg="white")
        actions.pack(side=tk.BOTTOM, anchor="e", padx=24, pady=(0, 10))
        for text, cmd, color in (
                ("💾 Сохранить проект", self.save_project_action, "white"),
                ("📄 Экспорт PDF (A4)", self.export_pdf_action, BLUE),
                ("📖 Инструкция по шитью", self.show_instructions_action, GREEN)):
            fg = DARK if color == "white" else "white"
            tk.Button(actions, text=text, command=cmd, relief=tk.FLAT,
                      bg=color, fg=fg, font=(ui_family(), 10, "bold"),
                      padx=14, pady=6,
                      highlightthickness=1,
                      highlightbackground=GRID_LIGHT).pack(side=tk.LEFT,
                                                           padx=6)

        status = tk.StringVar()
        self.preview = PreviewPanel(f, lambda: st.draft.pieces, status)
        self.preview.pack(fill=tk.BOTH, expand=True)
        self.after(120, self.preview.fit)
        self.after(450, self.preview.fit)

    # ---- действия результата ----
    def save_project_action(self):
        st = self.state
        project = Project()
        project.model_id = st.model.model_id
        project.model_title = st.model.title
        project.measurements = st.measurements
        project.params = st.params
        project.machine_key = st.machine_key
        project.size_label = st.size_label
        initial = os.path.basename(st.project_path) if st.project_path else (
            "SewMaster_%s_%s.sewproj" % (st.model.model_id,
                                         time.strftime("%Y%m%d")))
        path = filedialog.asksaveasfilename(
            parent=self, title="Сохранить проект",
            defaultextension=PROJECT_EXT,
            initialfile=initial,
            filetypes=[("Проект SewMaster", "*" + PROJECT_EXT),
                       ("Все файлы", "*.*")])
        if not path:
            return
        save_project(path, project)
        st.project_path = path
        settings = load_settings()
        remember_recent(path, settings)
        messagebox.showinfo("Проект сохранён",
                            "Файл проекта:\n%s\n\nОткройте его в любой момент, "
                            "чтобы изменить мерки и распечатать выкройку снова."
                            % path, parent=self)

    def export_pdf_action(self):
        st = self.state
        if st.draft is None:
            return
        settings = load_settings()
        name = "SewMaster_%s_%s.pdf" % (st.model.model_id,
                                        time.strftime("%Y-%m-%d"))
        last_dir = str(settings.get("last_pdf_dir", "") or "")
        dlg_kwargs = {}
        if last_dir and os.path.isdir(last_dir):
            dlg_kwargs["initialdir"] = last_dir
        path = filedialog.asksaveasfilename(
            parent=self, title="Экспорт выкройки в PDF",
            defaultextension=".pdf", initialfile=name,
            filetypes=[("PDF", "*.pdf"), ("Все файлы", "*.*")],
            **dlg_kwargs)
        if not path:
            return
        try:
            pages = export_pdf(path, st.model, st.measurements, st.params,
                               st.machine_key, st.draft,
                               size_label=st.size_label or "")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Ошибка экспорта",
                                 "Не удалось создать PDF:\n%s" % e, parent=self)
            return
        settings["last_pdf_dir"] = os.path.dirname(path)
        save_settings(settings)
        if messagebox.askyesno("PDF готов",
                               "Файл создан: %s\nСтраниц: %d\n\nОткрыть файл?"
                               % (path, pages), parent=self):
            from .theme import open_file
            open_file(path)

    def show_instructions_action(self):
        st = self.state
        if st.draft is None:
            return
        sections = build_instructions(st.model, st.measurements, st.params,
                                      st.machine_key, st.draft)
        windows.show_instructions(self, st, sections)

