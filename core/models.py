# -*- coding: utf-8 -*-
"""Реестр моделей одежды: описания, поля мерок и параметров, таблицы размеров.

Каждая модель (ModelDef) описывает:
  * какие мерки нужны и как их снимать (подсказки новичку),
  * параметры построения (посадка, прибавки, резинка, припуски),
  * тип построения draft_type, по которому вызывается генератор.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .drafts import BUILDERS
from .piece import DraftResult


class Field(object):
    """Поле мерки или параметра."""

    def __init__(self, key: str, label: str, hint: str = "",
                 typical: float = 0.0, vmin: float = 0.0, vmax: float = 0.0,
                 required: bool = True, unit: str = "см"):
        self.key = key
        self.label = label
        self.hint = hint
        self.typical = typical
        self.vmin = vmin
        self.vmax = vmax
        self.required = required
        self.unit = unit


class Choice(object):
    def __init__(self, value: object, label: str):
        self.value = value
        self.label = label


class ParamField(object):
    """Параметр построения: либо выбор из вариантов, либо число."""

    def __init__(self, key: str, label: str, hint: str = "",
                 choices: Optional[List[Choice]] = None,
                 vmin: float = 0.0, vmax: float = 0.0, default=None):
        self.key = key
        self.label = label
        self.hint = hint
        self.choices = choices
        self.vmin = vmin
        self.vmax = vmax
        self.default = default if default is not None else (
            choices[0].value if choices else vmin)


class ModelDef(object):
    def __init__(self, model_id: str, title: str, description: str,
                 draft_type: str, audience: str,
                 measurements: List[Field], params: List[ParamField],
                 fabric_hint: str):
        self.model_id = model_id
        self.title = title
        self.description = description
        self.draft_type = draft_type
        self.audience = audience          # 'women' | 'men' | 'uni'
        self.measurements = measurements
        self.params = params
        self.fabric_hint = fabric_hint
        self.source = "builtin"           # builtin | catalog
        self.default_params_override = None  # type: Optional[Dict[str, object]]

    # ---- значения по умолчанию -------------------------------------------
    def default_measurements(self) -> Dict[str, float]:
        return {f.key: f.typical for f in self.measurements}

    def default_params(self) -> Dict[str, object]:
        if self.default_params_override is not None:
            return dict(self.default_params_override)
        return {f.key: f.default for f in self.params}

    def build(self, meas: Dict[str, float], params: Dict[str, object]) -> DraftResult:
        builder = BUILDERS[self.draft_type]
        merged_p = self.default_params()
        merged_p.update(params or {})
        return builder(meas, merged_p)


# ============================ таблицы размеров ============================
# Типовые мерки (ГОСТ-подобные усреднённые значения). Пользователь может
# изменить любое значение вручную.

WOMEN_SIZES = {  # размер -> (Ог, От, Об)
    42: (84, 64, 92), 44: (88, 68, 96), 46: (92, 74, 100), 48: (96, 78, 104),
    50: (100, 82, 108), 52: (104, 86, 112), 54: (108, 92, 116),
    56: (112, 98, 120), 58: (116, 102, 124), 60: (120, 108, 128),
    62: (124, 112, 132),
}
MEN_SIZES = {    # размер -> (Ог, От, Об)
    44: (88, 78, 90), 46: (92, 82, 94), 48: (96, 86, 98), 50: (100, 90, 102),
    52: (104, 96, 106), 54: (108, 102, 110), 56: (112, 106, 114),
    58: (116, 110, 118), 60: (120, 114, 122), 62: (124, 118, 126),
}


def size_defaults(audience: str, size: int) -> Dict[str, float]:
    """Типовые мерки по размеру (без спец. мерок — их доберёт поле typical)."""
    table = MEN_SIZES if audience == "men" else WOMEN_SIZES
    chest, waist, hips = table.get(size, (100, 84, 106))
    return {"chest": float(chest), "waist": float(waist), "hips": float(hips),
            "rise": 27.0 if audience == "men" else 26.0}


# ============================ модели ======================================

MODELS = [
    ModelDef(
        "briefs", "Трусы-слипы", 
        "Классические трусы на резинке. Простая конструкция из двух полотнищ — "
        "лучший выбор для самого первого опыта шитья.",
        "briefs", "women",
        [
            Field("hips", "Обхват бёдер (Об)",
                  "Пройдите лентой по самым выступающим точкам бёдер и ягодиц, лента параллельна полу.",
                  100, 70, 170),
            Field("waist", "Обхват талии (От)",
                  "По самому узкому месту туловища. На выкройку не влияет — нужен только для расчёта резинки.",
                  78, 55, 150),
            Field("rise", "Высота сидения (Вс)",
                  "Сбоку от линии талии вертикально вниз до уровня промежности. Проще всего измерить сидя: от талии до поверхности стула, плюс 2-3 см.",
                  26, 16, 40),
        ],
        [
            ParamField("waist_style", "Посадка",
                       "Высота талии готовых трусов.",
                       choices=[Choice("classic", "Классическая"),
                                Choice("high", "Высокая (+2,5 см)"),
                                Choice("low", "Заниженная (-2,5 см)")]),
            ParamField("ease", "Свобода облегания, см",
                       "0-1 см — плотно по телу (для тянущегося трикотажа), 2-4 см — свободнее.",
                       vmin=0.0, vmax=4.0, default=1.0),
            ParamField("elastic_w", "Ширина резинки, см",
                       choices=[Choice(2.0, "2 см"), Choice(2.5, "2,5 см"),
                                Choice(3.0, "3 см"), Choice(4.0, "4 см")]),
            ParamField("allowance", "Припуск на швы, см",
                       "0,7 см — для трикотажа, 1-1,5 см — если хотите больше запаса на подгонку.",
                       choices=[Choice(0.7, "0,7 см"), Choice(1.0, "1 см"),
                                Choice(1.5, "1,5 см")]),
        ],
        "Трикотаж: кулирка с эластаном, интерлок, рибана. Расход ~50-60 см при ширине 150 см.",
    ),
    ModelDef(
        "boxers", "Трусы-боксёры",
        "Свободные трусы-шорты на резинке. Можно шить как из трикотажа, так и из лёгких тканей (сатин, байка).",
        "boxers", "uni",
        [
            Field("hips", "Обхват бёдер (Об)",
                  "По самым выступающим точкам бёдер и ягодиц.", 104, 70, 170),
            Field("rise", "Высота сидения (Вс)",
                  "Сбоку от талии вниз до уровня промежности (сидя: от талии до стула + 2-3 см).",
                  27, 16, 40),
            Field("side_len", "Длина по боку",
                  "От линии талии сбоку вниз до желаемого низа трусов. Классика: 28-32 см.",
                  30, 18, 60),
            Field("thigh", "Обхват бедра", 
                  "По самому широкому месту бедра (не обязательно — подставим типовое значение).",
                  62, 35, 100, required=False),
        ],
        [
            ParamField("ease", "Свобода облегания, см",
                       "2-3 см — обычная свобода, 4-6 см — очень свободные «домашние».",
                       vmin=0.0, vmax=8.0, default=2.0),
            ParamField("elastic_w", "Ширина резинки, см",
                       choices=[Choice(2.5, "2,5 см"), Choice(3.0, "3 см"),
                                Choice(4.0, "4 см"), Choice(5.0, "5 см")]),
            ParamField("allowance", "Припуск на швы, см",
                       choices=[Choice(0.7, "0,7 см"), Choice(1.0, "1 см"),
                                Choice(1.5, "1,5 см")]),
        ],
        "Трикотаж, байка, сатин, поплин. Расход ~70-80 см при ширине 150 см.",
    ),
    ModelDef(
        "tank", "Майка-безрукавка",
        "Майка с цельнокроеными бретелями («алкоголичка»). Кроится из двух деталей на сгибе.",
        "tank", "uni",
        [
            Field("chest", "Обхват груди (Ог)",
                  "По самым выступающим точкам груди, лента параллельно полу.", 92, 70, 150),
            Field("hips", "Обхват бёдер (Об)",
                  "Нужен для ширины низа майки (не обязательно).", 100, 70, 170,
                  required=False),
            Field("length", "Длина изделия",
                  "От высокой точки плеча у шеи вниз до желаемого низа.", 60, 35, 90),
        ],
        [
            ParamField("fit", "Крой",
                       choices=[Choice("fit", "Облегающий"),
                                Choice("free", "Свободный")]),
            ParamField("strap_w", "Ширина бретели, см",
                       "3-4 см — обычно, 5-6 см — спортивный вариант.",
                       vmin=2.5, vmax=7.0, default=4.0),
            ParamField("neck_front", "Глубина горловины спереди, см",
                       "7-8 см — стандарт, больше — декольтивнее.",
                       vmin=5.0, vmax=14.0, default=7.5),
            ParamField("allowance", "Припуск на швы, см",
                       choices=[Choice(0.7, "0,7 см"), Choice(1.0, "1 см"),
                                Choice(1.5, "1,5 см")]),
        ],
        "Трикотаж: кулирка, интерлок. Расход ~1,3-1,5 м при ширине 150 см.",
    ),
    ModelDef(
        "tee", "Футболка (спущенное плечо)",
        "Футболка со спущенным плечом — самый простой крой с рукавом. Рукав без сложного оката, втачивается по прямой.",
        "tee", "uni",
        [
            Field("chest", "Обхват груди (Ог)", 
                  "По самым выступающим точкам груди, лента параллельно полу.", 96, 70, 150),
            Field("hips", "Обхват бёдер (Об)",
                  "Для ширины низа (не обязательно).", 100, 70, 170, required=False),
            Field("length", "Длина изделия",
                  "От высокой точки плеча у шеи до желаемого низа.", 68, 40, 95),
            Field("neck", "Обхват шеи (Ош)",
                  "По основанию шеи, спереди по яремной ямке, сзади по 7-му шейному позвонку.",
                  37, 28, 55),
            Field("sleeve_len", "Длина рукава",
                  "От плечевой точки вниз по наружной стороне руки до желаемого низа рукава. Короткий рукав: 18-25 см.",
                  22, 8, 65),
            Field("arm", "Обхват плеча (Оп)",
                  "По самому широкому месту руки (бицепс), рука расслаблена.", 30, 20, 60),
        ],
        [
            ParamField("fit", "Крой",
                       choices=[Choice("fit", "Обычный"),
                                Choice("over", "Оверсайз")]),
            ParamField("allowance", "Припуск на швы, см",
                       choices=[Choice(0.7, "0,7 см"), Choice(1.0, "1 см"),
                                Choice(1.5, "1,5 см")]),
        ],
        "Трикотаж: кулирка, интерлок, футер. Расход ~1,6-2 м при ширине 150 см.",
    ),
]

MODELS_BY_ID = {m.model_id: m for m in MODELS}


def get_model(model_id: str) -> Optional[ModelDef]:
    return MODELS_BY_ID.get(model_id)
