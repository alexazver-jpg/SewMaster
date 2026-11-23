# -*- coding: utf-8 -*-
"""Пути к ресурсам (корректно работает и в исходниках, и внутри .exe PyInstaller)."""
from __future__ import annotations

import os
import sys

APP_NAME = "SewMaster"
APP_VERSION = "1.0.1"


def project_root() -> str:
    """Каталог с assets/ и т.д. В заморожённом exe — sys._MEIPASS."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset_path(*parts: str) -> str:
    return os.path.join(project_root(), "assets", *parts)


def app_data_dir() -> str:
    """Каталог пользовательских данных (настройки, каталог выкроек)."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        path = os.path.expanduser("~")
    return path
