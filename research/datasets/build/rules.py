from __future__ import annotations

EXCLUSIONS: dict[str, str] = {
    "attr12090": (
        "pilot_scope: no ground truth in current PDF set "
        "(Максимальный крутящий момент на выходном валу арматуры при перемещении на закрытие)"
    ),
    "attr12091": (
        "pilot_scope: no ground truth in current PDF set "
        "(Максимальный крутящий момент на выходном валу арматуры при перемещении на открытие)"
    ),
    "attr10533": (
        "pilot_policy: no ground truth in current PDF set (Категория сварного соединения)"
    ),
    # Always missing among required gids in handmade PDF set (build GT check).
    "attr336": "pilot_scope: no ground truth in current PDF set (Сезонность)",
    "attr11223": "pilot_scope: no ground truth in current PDF set (Категория трубопровода)",
    "attr7763": "pilot_scope: no ground truth in current PDF set (Рабочая среда)",
    "attr1762": "pilot_scope: no ground truth in current PDF set (Внутренний диаметр)",
    "attr2789": "pilot_scope: no ground truth in current PDF set (Пределы измерения по шкале)",
    "attr11295": "pilot_scope: no ground truth in current PDF set (Полнота обуви)",
    "attr1486": "pilot_scope: no ground truth in current PDF set (Диаметр трубопровода)",
    "attr11835": "pilot_scope: no ground truth in current PDF set (Размер фаски)",
    "attr11836": "pilot_scope: no ground truth in current PDF set (Угол фаски)",
    "attr11837": "pilot_scope: no ground truth in current PDF set (Радиус закругления вершины)",
    "attr11917": "pilot_scope: no ground truth in current PDF set (Диаметр обнижения)",
    "attr11918": "pilot_scope: no ground truth in current PDF set (Длина обнижения)",
}


def apply_extraction_flags(attr: dict) -> dict:
    exclusion_reason = EXCLUSIONS.get(attr["attr_id"])
    attr["for_extraction"] = exclusion_reason is None
    attr["exclusion_reason"] = exclusion_reason
    return attr
