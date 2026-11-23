# -*- coding: utf-8 -*-
"""SewMaster — точка входа приложения."""
from __future__ import annotations

import sys
import traceback


def main():
    # Чёткость текста на экранах с высоким DPI (Windows)
    if sys.platform.startswith("win"):
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    import tkinter as tk
    from tkinter import messagebox
    from gui.windows import MainWindow

    root = MainWindow()
    root.report_callback_exception = lambda *a: (
        traceback.print_exception(*a),
        messagebox.showerror(
            "SewMaster — ошибка",
            "Произошла непредвиденная ошибка:\n%s\n\n"
            "Попробуйте повторить действие. Если ошибка повторяется, "
            "сообщите в GitHub Issues." % a[1]))
    root.mainloop()


if __name__ == "__main__":
    main()
