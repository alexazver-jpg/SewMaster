# -*- coding: utf-8 -*-
"""Окна приложения: главное, инструкция, онлайн-каталог, справка по меркам."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List, Optional

from core import catalog as catalog_mod
from core.instructions import instructions_to_text
from core.models import MODELS
from core.storage import Project, load_project, load_settings, remember_recent
from core.storage import PROJECT_EXT
from .theme import (BG, BLUE, BLUE_BG, BLUE_LIGHT, DARK, GRAY, GREEN,
                    GRID, GRID_LIGHT, open_file, ui_family)

APP_TITLE = "SewMaster — конструктор выкроек"


def center_window(win):
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry("+%d+%d" % (x, max(0, y - 40)))


def page_header(parent, title: str, subtitle: str):
    head = tk.Frame(parent, bg="white")
    head.pack(fill=tk.X)
    tk.Label(head, text=title, bg="white", fg=DARK,
             font=(ui_family(), 15, "bold")).pack(anchor="w", padx=24,
                                                 pady=(16, 2))
    tk.Label(head, text=subtitle, bg="white", fg=GRAY,
             font=(ui_family(), 10), wraplength=880,
             justify=tk.LEFT).pack(anchor="w", padx=24, pady=(0, 14))


def draw_thumb(canvas: tk.Canvas, draft, pad: float = 4.0):
    """Мини-превью деталей выкройки на маленьком холсте."""
    if not draft or not draft.pieces:
        return
    xs0, ys0, xs1, ys1 = [], [], [], []
    for p in draft.pieces:
        x0, y0, x1, y1 = p.bbox(True)
        xs0.append(x0); ys0.append(y0); xs1.append(x1); ys1.append(y1)
    x0, y0, x1, y1 = min(xs0), min(ys0), max(xs1), max(ys1)
    W = canvas.winfo_reqwidth() - 8
    H = canvas.winfo_reqheight() - 8
    sx = W / max(x1 - x0 + 2 * pad, 1e-6)
    sy = H / max(y1 - y0 + 2 * pad, 1e-6)
    s = min(sx, sy)

    def T(p):
        return (4 + (p[0] - x0 + pad) * s, 4 + (p[1] - y0 + pad) * s)

    for piece in draft.pieces:
        cut = [T(p) for p in piece.cut_poly]
        if len(cut) > 2:
            canvas.create_polygon(cut, fill="#eef2ff", outline=DARK, width=1)
        seam = [T(p) for p in piece.contour.points(16)]
        seam.append(T(piece.contour.start))
        canvas.create_line(seam, fill="#dc2626", width=1, dash=(3, 2))


# ============================ главное окно ============================

class MainWindow(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(APP_TITLE)
        self.geometry("1000x740")
        self.minsize(900, 640)
        self.configure(bg=BG)

        # ---- шапка ----
        head = tk.Frame(self, bg=BLUE)
        head.pack(fill=tk.X)
        tk.Label(head, text="SewMaster", bg=BLUE, fg="white",
                 font=(ui_family(), 20, "bold")).pack(side=tk.LEFT,
                                                     padx=24, pady=14)
        tk.Label(head, text="конструктор выкроек для домашнего пошива",
                 bg=BLUE, fg=BLUE_LIGHT, font=(ui_family(), 10)).pack(
                     side=tk.LEFT, pady=(18, 0))
        from core.paths import APP_VERSION
        tk.Label(head, text="v" + APP_VERSION, bg=BLUE, fg=BLUE_LIGHT,
                 font=(ui_family(), 9)).pack(side=tk.RIGHT, padx=24)

        # ---- карточки действий ----
        cards = tk.Frame(self, bg=BG)
        cards.pack(fill=tk.X, padx=24, pady=18)
        data = [
            ("🧵  Новая выкройка", "Трусы, шорты, майка, футболка, лонгслив,\n"
             "юбка — мастер за 5 шагов", self.new_pattern, BLUE),
            ("📂  Открыть проект", "Ранее сохранённые мерки\nи выкройки",
             self.open_project, "white"),
            ("🌐  Онлайн-каталог", "Скачать дополнительные модели\n"
             "выкроек из интернета", self.show_catalog, "white"),
            ("📏  Как снимать мерки", "Иллюстрированная памятка\nдля новичка",
             self.show_help, "white"),
        ]
        for i, (title, sub, cmd, color) in enumerate(data):
            card = tk.Frame(cards, bg=color, highlightthickness=1,
                            highlightbackground=GRID_LIGHT)
            card.grid(row=0, column=i, padx=8, sticky="nsew")
            cards.grid_columnconfigure(i, weight=1)
            fg = "white" if color == BLUE else DARK
            subfg = BLUE_LIGHT if color == BLUE else GRAY
            tk.Label(card, text=title, bg=color, fg=fg,
                     font=(ui_family(), 12, "bold")).pack(pady=(16, 4), padx=10)
            tk.Label(card, text=sub, bg=color, fg=subfg,
                     font=(ui_family(), 9), justify=tk.CENTER).pack(padx=10)
            tk.Button(card, text="Открыть", command=cmd, relief=tk.FLAT,
                      bg=BLUE if color != BLUE else "white",
                      fg="white" if color != BLUE else BLUE,
                      font=(ui_family(), 9, "bold"), padx=12, pady=3
                      ).pack(pady=(8, 16))

        # ---- доступные модели (карточки в несколько рядов) ----
        tk.Label(self, text="Встроенные модели", bg=BG, fg=DARK,
                 font=(ui_family(), 12, "bold")).pack(anchor="w", padx=26,
                                                      pady=(10, 2))
        models_frame = tk.Frame(self, bg=BG)
        models_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 8))
        n_models = len(MODELS)
        for i, model in enumerate(MODELS):
            row, col = divmod(i, 4)
            card = tk.Frame(models_frame, bg="white", highlightthickness=1,
                            highlightbackground=GRID_LIGHT)
            card.grid(row=row, column=col, padx=8, pady=6, sticky="nsew")
            models_frame.grid_columnconfigure(col, weight=1)
            models_frame.grid_rowconfigure(row, weight=1)
            try:
                draft = model.build(model.default_measurements(),
                                    model.default_params())
                thumb = tk.Canvas(card, width=180, height=115, bg="white",
                                  highlightthickness=0)
                thumb.pack(padx=8, pady=(8, 0))
                draw_thumb(thumb, draft)
            except Exception:
                thumb = tk.Canvas(card, width=180, height=115, bg="white",
                                  highlightthickness=0)
                thumb.pack(padx=8, pady=(8, 0))
            tk.Label(card, text=model.title, bg="white", fg=DARK,
                     font=(ui_family(), 9, "bold"), wraplength=180,
                     height=2).pack(pady=(2, 0))
            tk.Label(card, text=model.fabric_hint, bg="white", fg=GRAY,
                     font=(ui_family(), 8), wraplength=170,
                     justify=tk.LEFT).pack(padx=6, pady=(0, 4))

        # ---- последние проекты ----
        settings = load_settings()
        recent = [str(p) for p in settings.get("recent", [])
                  if os.path.exists(str(p))][:5]
        if recent:
            tk.Label(self, text="Последние проекты", bg=BG, fg=DARK,
                     font=(ui_family(), 11, "bold")).pack(anchor="w", padx=26,
                                                         pady=(8, 2))
            box = tk.Frame(self, bg=BG)
            box.pack(fill=tk.X, padx=24, pady=(0, 10))
            for path in recent:
                name = os.path.basename(path)
                tk.Button(box, text="📄 " + name, relief=tk.FLAT, bg="white",
                          fg=DARK, font=(ui_family(), 9), anchor="w",
                          padx=10, pady=2, highlightthickness=1,
                          highlightbackground=GRID_LIGHT,
                          command=lambda p=path: self.open_path(p)
                          ).pack(side=tk.LEFT, padx=4)

        # подсказка внизу
        tk.Label(self, text="Программа работает без интернета. Онлайн нужен "
                 "только для скачивания моделей из каталога.",
                 bg=BG, fg=GRAY, font=(ui_family(), 8)).pack(pady=(0, 8))

    # ---- обработчики ----
    def new_pattern(self):
        from .wizard import Wizard
        Wizard(self)

    def open_path(self, path: str):
        try:
            project = load_project(path)
        except ValueError as e:
            messagebox.showerror("Открытие проекта", str(e))
            return
        model = None
        from core.models import get_model
        model = get_model(project.model_id)
        if model is None:
            # возможно, модель из каталога
            for m in catalog_mod.list_local_catalog_models():
                if m.model_id == project.model_id:
                    model = m
                    break
        if model is None:
            messagebox.showerror("Открытие проекта",
                                 "Модель «%s» не найдена в программе.\n"
                                 "Возможно, её нужно скачать в онлайн-каталоге."
                                 % project.model_id)
            return
        from .wizard import Wizard, WizardState
        state = WizardState()
        state.model = model
        state.measurements = project.measurements
        state.params = project.params
        state.machine_key = project.machine_key
        state.size_label = project.size_label
        state.project_path = path
        state.audience.set(model.audience if model.audience != "uni"
                           else "women")
        state.draft = model.build(project.measurements, project.params)
        settings = load_settings()
        remember_recent(path, settings)
        Wizard(self, state=state, start_step=4)

    def open_project(self):
        path = filedialog.askopenfilename(
            title="Открыть проект SewMaster",
            filetypes=[("Проект SewMaster", "*" + PROJECT_EXT),
                       ("Все файлы", "*.*")])
        if path:
            self.open_path(path)

    def show_catalog(self):
        CatalogWindow(self)

    def show_help(self):
        HelpWindow(self)


# ============================ окно каталога ============================

class CatalogWindow(tk.Toplevel):
    def __init__(self, master):
        tk.Toplevel.__init__(self, master)
        self.title("Онлайн-каталог SewMaster")
        self.geometry("720x520")
        self.configure(bg=BG)
        page_header(self, "Онлайн-каталог моделей",
                    "Скачайте дополнительные выкройки из репозитория SewMaster "
                    "на GitHub. Скачанные модели появятся в списке моделей.")

        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill=tk.X, padx=24)
        tk.Button(toolbar, text="⟳  Обновить каталог", relief=tk.FLAT, bg=BLUE,
                  fg="white", font=(ui_family(), 10, "bold"), padx=14, pady=5,
                  command=self.refresh).pack(side=tk.LEFT)
        self.status = tk.Label(toolbar, text="", bg=BG, fg=GRAY,
                               font=(ui_family(), 9))
        self.status.pack(side=tk.LEFT, padx=12)

        self.list_frame = tk.Frame(self, bg="white", highlightthickness=1,
                                   highlightbackground=GRID_LIGHT)
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=10)

        self.show_local()

    def refresh(self):
        self.status.config(text="Загружаю каталог из интернета…")
        try:
            data = catalog_mod.fetch_catalog()
        except Exception as e:  # noqa: BLE001
            self.status.config(text="")
            messagebox.showwarning("Каталог",
                                   "Не удалось загрузить каталог:\n%s\n\n"
                                   "Проверьте подключение к интернету." % e,
                                   parent=self)
            return
        self.status.config(text="Каталог загружен, доступно моделей: %d"
                           % len(data.get("models", [])))
        self.entries = list(data.get("models", []))
        self.render_entries()

    def show_local(self):
        self.entries = []
        self.render_entries(include_local=True)

    def render_entries(self, include_local: bool = False):
        for w in self.list_frame.winfo_children():
            w.destroy()
        row = 0
        if include_local:
            local = catalog_mod.list_local_catalog_models()
            if local:
                tk.Label(self.list_frame, text="Уже скачанные модели",
                         bg="white", fg=GREEN, font=(ui_family(), 10, "bold")
                         ).grid(row=row, column=0, columnspan=2, sticky="w",
                                padx=14, pady=(10, 2))
                row += 1
                for m in local:
                    self._row(row, m.title, m.description,
                              "удалить", lambda mid=m.model_id: self.remove_local(mid))
                    row += 1
                row += 1
        if not self.entries:
            tk.Label(self.list_frame, bg="white", fg=GRAY,
                     text="Нажмите «Обновить каталог», чтобы увидеть доступные "
                          "для скачивания модели.", font=(ui_family(), 10),
                     justify=tk.LEFT).grid(row=row, column=0, padx=14,
                                           pady=16, sticky="w")
            return
        tk.Label(self.list_frame, text="Доступно для скачивания", bg="white",
                 fg=DARK, font=(ui_family(), 10, "bold")).grid(
                     row=row, column=0, columnspan=2, sticky="w", padx=14,
                     pady=(10, 2))
        row += 1
        for entry in self.entries:
            model = catalog_mod.catalog_model_to_def(entry)
            if model is None:
                continue
            def do_download(m=model):
                catalog_mod.save_catalog_model(m)
                messagebox.showinfo("Каталог",
                                    "Модель «%s» скачана и добавлена в список."
                                    % m.title, parent=self)
                self.show_local()
            self._row(row, model.title, model.description, "скачать",
                      do_download)
            row += 1

    def _row(self, row, title, desc, action_text, action_cmd):
        tk.Label(self.list_frame, text=title, bg="white", fg=DARK,
                 font=(ui_family(), 10, "bold")).grid(row=row, column=0,
                                                     sticky="w", padx=14,
                                                     pady=4)
        tk.Label(self.list_frame, text=(desc or "")[:90], bg="white", fg=GRAY,
                 font=(ui_family(), 8), wraplength=420, justify=tk.LEFT
                 ).grid(row=row, column=1, sticky="w", padx=4, pady=4)
        tk.Button(self.list_frame, text=action_text, relief=tk.FLAT, bg=BLUE,
                  fg="white", font=(ui_family(), 8, "bold"), padx=10,
                  command=action_cmd).grid(row=row, column=2, padx=(4, 14),
                                           pady=4)

    def remove_local(self, model_id):
        catalog_mod.delete_local_catalog_model(model_id)
        self.show_local()


# ============================ окно инструкции ============================

def show_instructions(master, state, sections):
    win = tk.Toplevel(master)
    win.title("Инструкция по шитью — %s" % state.model.title)
    win.geometry("820x680")
    win.configure(bg=BG)

    text = instructions_to_text(sections)

    head = tk.Frame(win, bg="white")
    head.pack(fill=tk.X)
    tk.Label(head, text="Инструкция по шитью: %s" % state.model.title,
             bg="white", fg=DARK, font=(ui_family(), 13, "bold")).pack(
                 side=tk.LEFT, padx=18, pady=10)
    tk.Button(head, text="Копировать текст", relief=tk.FLAT, bg="white",
              fg=DARK, font=(ui_family(), 9), padx=10,
              command=lambda: copy_text(win, text)).pack(side=tk.RIGHT,
                                                          padx=8)
    tk.Button(head, text="Сохранить в .txt", relief=tk.FLAT, bg="white",
              fg=DARK, font=(ui_family(), 9), padx=10,
              command=lambda: save_txt(win, state, text)).pack(side=tk.RIGHT)

    box = tk.Frame(win, bg=BG)
    box.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
    scroll = tk.Scrollbar(box)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    txt = tk.Text(box, wrap=tk.WORD, font=(ui_family(), 10), bd=0,
                  highlightthickness=0, padx=14, pady=10)
    txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.config(command=txt.yview)
    txt.config(yscrollcommand=scroll.set)

    # форматирование
    txt.tag_configure("h1", font=(ui_family(), 12, "bold"), foreground=BLUE,
                      spacing1=14, spacing3=4)
    txt.tag_configure("h2", font=(ui_family(), 10, "bold"), foreground=DARK,
                      spacing1=10, spacing3=3)
    txt.tag_configure("step", font=(ui_family(), 10, "bold"), foreground=DARK,
                      spacing1=10)
    txt.tag_configure("body", foreground="#1f2937", spacing3=4)
    txt.tag_configure("tip", foreground=GREEN, lmargin1=14, spacing3=4)
    txt.tag_configure("warn", foreground="#b91c1c", lmargin1=14, spacing3=4)

    import re
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("===") or not s:
            continue
        if re.match(r"^[А-ЯЁ0-9 ]{6,}$", s) and s == s.upper():
            txt.insert(tk.END, s + "\n", "h1")
        elif s.startswith("ШАГ "):
            txt.insert(tk.END, s + "\n", "step")
        elif s.startswith("СОВЕТ:"):
            txt.insert(tk.END, s + "\n", "tip")
        elif s.startswith("ВАЖНО:"):
            txt.insert(tk.END, s + "\n", "warn")
        elif s.startswith("-"):
            txt.insert(tk.END, s + "\n", "h2")
        else:
            txt.insert(tk.END, line + "\n", "body")
    txt.config(state=tk.DISABLED)
    center_window(win)
    return win


def copy_text(win, text):
    win.clipboard_clear()
    win.clipboard_append(text)
    messagebox.showinfo("Инструкция",
                        "Текст инструкции скопирован в буфер обмена.",
                        parent=win)


def save_txt(win, state, text):
    path = filedialog.asksaveasfilename(
        parent=win, title="Сохранить инструкцию", defaultextension=".txt",
        initialfile="Инструкция_%s.txt" % state.model.model_id,
        filetypes=[("Текстовый файл", "*.txt")])
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    messagebox.showinfo("Инструкция", "Сохранено: %s" % path, parent=win)


# ============================ справка по меркам ============================

class HelpWindow(tk.Toplevel):
    MEASURE_HELP = (
        ("Обхват груди (Ог)", "По самым выступающим точкам груди. Лента — "
         "горизонтально, параллельно полу. Дышите спокойно, не на вдохе."),
        ("Обхват талии (От)", "По самому узкому месту туловища. Не втягивайте "
         "живот: трусы должны сидеть комфортно."),
        ("Обхват бёдер (Об)", "По самым выступающим точкам бёдер и ягодиц, "
         "лента параллельно полу."),
        ("Высота сидения (Вс)", "Сбоку — от линии талии вертикально вниз до "
         "уровня промежности. Проще измерить сидя на твёрдом стуле: от талии "
         "до поверхности сиденья, плюс 2-3 см."),
        ("Обхват шеи (Ош)", "По основанию шеи: спереди — над яремной ямкой, "
         "сзади — по выступающему позвонку."),
        ("Обхват плеча (Оп)", "По самому широкому месту руки (бицепс), "
         "рука расслаблена и опущена."),
        ("Длина изделия", "От высокой точки плеча у шеи вниз по фигуре до "
         "желаемого уровня низа."),
        ("Обхват бедра", "По самому широкому месту бедра (под ягодицей)."))

    def __init__(self, master):
        tk.Toplevel.__init__(self, master)
        self.title("Как снимать мерки")
        self.geometry("680x560")
        self.configure(bg=BG)
        page_header(self, "Как снимать мерки",
                    "Сантиметровая лента должна прилегать плотно, но не "
                    "стягивать фигуру. Измеряйте поверх тонкой одежды или "
                    "белья.")
        body = tk.Frame(self, bg="white", highlightthickness=1,
                        highlightbackground=GRID_LIGHT)
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        for i, (name, how) in enumerate(self.MEASURE_HELP):
            tk.Label(body, text="• " + name, bg="white", fg=DARK,
                     font=(ui_family(), 10, "bold")).grid(row=i, column=0,
                                                         sticky="nw",
                                                         padx=(14, 6),
                                                         pady=5)
            tk.Label(body, text=how, bg="white", fg=GRAY,
                     font=(ui_family(), 9), wraplength=460, justify=tk.LEFT
                     ).grid(row=i, column=1, sticky="nw", padx=(0, 14),
                            pady=5)
        body.grid_columnconfigure(1, weight=1)
