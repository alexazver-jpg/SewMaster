# -*- coding: utf-8 -*-
"""Сохранение и загрузка проектов SewMaster (.sewproj) и настроек."""
from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Optional

from .paths import APP_VERSION, app_data_dir

PROJECT_EXT = ".sewproj"
FORMAT_VERSION = 1


class Project(object):
    """Проект: модель + мерки + параметры + машина."""

    def __init__(self):
        self.model_id = ""
        self.model_title = ""
        self.measurements = {}  # type: Dict[str, float]
        self.params = {}        # type: Dict[str, object]
        self.machine_key = "zigzag"
        self.size_label = ""
        self.notes = ""
        self.created = ""
        self.app_version = APP_VERSION

    # ---- сериализация -----------------------------------------------------
    def to_dict(self) -> Dict[str, object]:
        return {
            "format_version": FORMAT_VERSION,
            "app_version": self.app_version,
            "model_id": self.model_id,
            "model_title": self.model_title,
            "measurements": self.measurements,
            "params": self.params,
            "machine_key": self.machine_key,
            "size_label": self.size_label,
            "notes": self.notes,
            "created": self.created or time.strftime("%Y-%m-%d %H:%M"),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Project":
        p = cls()
        p.model_id = str(data.get("model_id", ""))
        p.model_title = str(data.get("model_title", ""))
        p.measurements = dict(data.get("measurements", {}))
        p.params = dict(data.get("params", {}))
        p.machine_key = str(data.get("machine_key", "zigzag"))
        p.size_label = str(data.get("size_label", ""))
        p.notes = str(data.get("notes", ""))
        p.created = str(data.get("created", ""))
        ver = data.get("app_version")
        if ver:
            p.app_version = str(ver)
        return p


def save_project(path: str, project: Project) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project.to_dict(), f, ensure_ascii=False, indent=2)


def load_project(path: str) -> Optional[Project]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if int(data.get("format_version", 0)) > FORMAT_VERSION:
            raise ValueError("Файл создан более новой версией SewMaster")
        return Project.from_dict(data)
    except (OSError, ValueError) as e:
        raise ValueError("Не удалось открыть проект: %s" % e)


# ----------------------------- настройки ---------------------------------

def _settings_path() -> str:
    return os.path.join(app_data_dir(), "settings.json")


def load_settings() -> Dict[str, object]:
    try:
        with open(_settings_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(settings: Dict[str, object]) -> None:
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def remember_recent(path: str, settings: Dict[str, object]) -> None:
    recent = [str(x) for x in settings.get("recent", [])]
    if path in recent:
        recent.remove(path)
    recent.insert(0, path)
    settings["recent"] = recent[:8]
    save_settings(settings)
