# -*- coding: utf-8 -*-
"""Онлайн-каталог моделей выкроек.

Каталог — это JSON-файл в GitHub-репозитории проекта. Пользователь может
скачать дополнительные модели (пресеты параметров для встроенных типов
построения) без обновления программы. Скачанные модели сохраняются в
каталоге данных приложения и появляются в списке моделей.

Схема каталога (catalog/index.json):
{
  "catalog_version": 1,
  "models": [
    {
      "id": "briefs_high",
      "title": "Трусы-слипы, высокая посадка",
      "description": "...",
      "draft_type": "briefs",        # тип построения из core.drafts.BUILDERS
      "audience": "women",
      "params": {"waist_style": "high", "elastic_w": 3.0},   # пресет параметров
      "fabric_hint": "..."
    }
  ],
  "links": [ {"title": "...", "url": "https://..."} ]
}
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Dict, List, Optional

from .models import Choice, Field, ModelDef, ParamField

CATALOG_URL = ("https://raw.githubusercontent.com/alexazver-jpg/SewMaster/"
               "main/catalog/index.json")
TIMEOUT_SEC = 12


def local_catalog_dir() -> str:
    from .paths import app_data_dir
    path = os.path.join(app_data_dir(), "catalog")
    os.makedirs(path, exist_ok=True)
    return path


def fetch_catalog(url: str = CATALOG_URL) -> Dict[str, object]:
    """Загружает индекс каталога из интернета. Бросает OSError при сбое."""
    req = urllib.request.Request(url, headers={"User-Agent": "SewMaster/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict) or "models" not in data:
        raise ValueError("Неверный формат каталога")
    return data


def catalog_model_to_def(entry: Dict[str, object]) -> Optional[ModelDef]:
    """Превращает запись каталога в ModelDef (модель с пресетом параметров)."""
    from .models import MODELS_BY_ID
    try:
        base = MODELS_BY_ID[str(entry.get("base_model", ""))]
    except KeyError:
        return None
    # переопределение типовых мерок (например, длина изделия)
    meas_over = entry.get("measurements", {}) or {}
    measurements = []
    for f in base.measurements:
        if f.key in meas_over:
            f = Field(f.key, f.label, f.hint, float(meas_over[f.key]),
                      f.vmin, f.vmax, f.required, f.unit)
        measurements.append(f)
    params = {}
    for pf in base.params:
        value = entry.get("params", {}).get(pf.key)
        if value is not None:
            if pf.choices:
                value = value  # выбор проверим при сборке
            else:
                value = float(value)
        else:
            value = pf.default
        params[pf.key] = value
    model = ModelDef(
        model_id=str(entry.get("id", "catalog_model")),
        title=str(entry.get("title", base.title)),
        description=str(entry.get("description", base.description)),
        draft_type=base.draft_type,
        audience=base.audience,
        measurements=measurements,
        params=list(base.params),
        fabric_hint=str(entry.get("fabric_hint", base.fabric_hint)),
    )
    model.source = "catalog"
    model.default_params_override = params
    return model


def save_catalog_model(model: ModelDef) -> str:
    """Сохраняет скачанную модель локально. Возвращает путь к файлу."""
    from .models import MODELS_BY_ID
    base = MODELS_BY_ID.get(model.draft_type and _base_id_of(model))
    data = {
        "id": model.model_id,
        "title": model.title,
        "description": model.description,
        "base_model": _base_id_of(model),
        "draft_type": model.draft_type,
        "params": getattr(model, "default_params_override", {}),
        "fabric_hint": model.fabric_hint,
    }
    path = os.path.join(local_catalog_dir(), model.model_id + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _base_id_of(model: ModelDef) -> str:
    # по draft_type находим встроенную модель-основу
    from .models import MODELS
    for m in MODELS:
        if m.draft_type == model.draft_type:
            return m.model_id
    return ""


def list_local_catalog_models() -> List[ModelDef]:
    """Список ранее скачанных моделей из локального хранилища."""
    out = []
    try:
        names = os.listdir(local_catalog_dir())
    except OSError:
        return out
    for name in sorted(names):
        if not name.endswith(".json"):
            continue
        path = os.path.join(local_catalog_dir(), name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                entry = json.load(f)
            model = catalog_model_to_def(entry)
            if model:
                out.append(model)
        except (OSError, ValueError):
            continue
    return out


def delete_local_catalog_model(model_id: str) -> None:
    path = os.path.join(local_catalog_dir(), model_id + ".json")
    try:
        os.remove(path)
    except OSError:
        pass
