# -*- coding: utf-8 -*-
"""Реестр построителей выкроек по типу модели."""
from __future__ import annotations

from typing import Callable, Dict

from . import briefs, boxers, tank, tee, skirt_sun, shorts, longsleeve

# draft_type -> функция построения (мерки, параметры) -> DraftResult
BUILDERS = {
    "briefs": briefs.build,
    "boxers": boxers.build,
    "tank": tank.build,
    "tee": tee.build,
    "skirt_sun": skirt_sun.build,
    "shorts": shorts.build,
    "longsleeve": longsleeve.build,
}  # type: Dict[str, Callable]
