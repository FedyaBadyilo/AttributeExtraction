# Шаг: attribute_grouping

## Назначение

Семантическая группировка атрибутов класса НСИ для последующего совместного извлечения из технических документов.

Шаг разбивает атрибуты одного класса (с флагом `for_extraction=True`) на непересекающиеся группы:

- Атрибуты с высоким косинусным сходством эмбеддингов объединяются в «tight groups» через Union–Find.
- Остаток разбивается на партиции и отправляется в LLM для семантической группировки.
- Атрибуты, не попавшие ни в одну LLM-группу, становятся группами-одиночками.
- Каждый атрибут входит ровно в одну группу (coverage guarantee).

## Входные данные

`research/datasets/processed/class_attribute_sets.json` — словарь вида:

```json
{
  "class_code": [
    {
      "attr_id": "...",
      "attr_name": "...",
      "descr": "...",
      "attr_type": "Строка",
      "units": ["мм", "м", "см"],
      "allowed_values": ["значение1", "значение2"],
      "for_extraction": true
    }
  ]
}
```

Поле `attr_type` принимает NCI-строки: `Строка`, `Вещественное число`, `Целое число`, `Диапазон`, `Список`, `Набор значений`.

`units` и `allowed_values` опциональные.

## Выходные данные

`output/attribute_groups.json` — один файл, ключ верхнего уровня — `class_code`:

```json
{
  "demo-valve": {
    "groups": [
      {"attr_ids": ["attr_dn", "attr_pn"]},
      {"attr_ids": ["attr_body_material"]}
    ]
  }
}
```

## Запуск

```bash
python -m research.steps.attribute_grouping.run
```