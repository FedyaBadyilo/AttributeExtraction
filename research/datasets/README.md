# Datasets

Зона данных research-пайплайна: как собираются processed-артефакты, где лежит OCR-benchmark и как шаги читают манифест/GT.

| Путь | Назначение |
| --- | --- |
| `demo/` | Synthetic demo-пакет (`demo-motor`) для smoke / mock / app seed — [`demo/README.md`](demo/README.md) |
| `build/` | Сборка processed из Excel-реестра PDF + PostgreSQL (нужны `DB_*`) |
| `ocr_benchmark/` | Контракт OCR-бенчмарка: `manifest.json`, reference markdown, fixtures |
| `processed/` | Processed JSON/JSONL для debug-прогонов шагов (локально; каталог может быть пустым без своего пакета) |
| `access.py` | Defaults путей и загрузка `examples_manifest` / class sets / GT |
| `tests/` | Тесты helpers сборки GT |

Сырые PDF и выгрузки БД в git не кладём (`data.local/`, см. `.gitignore`).

## Processed-контракт

Три артефакта, которые едят шаги пайплайна:

| Файл | Содержание |
| --- | --- |
| `examples_manifest.json` | примеры: id карточки, имя PDF, приоритет, `class_code` |
| `class_attribute_sets.json` | атрибуты по классам + `for_extraction` |
| `ground_truth.jsonl` | эталон `(gid, attr_id, attr_name, value)` |

Сборка и детали CLI — в [`build/README.md`](build/README.md).

## OCR benchmark

Маленький synthetic-контракт под scoring document parsing:

- `manifest.json` — кейсы (born-digital + image-only scan)
- `markdown_reference/` — эталонный markdown
- `fixtures/` — PDF для input/source

Подробности кейсов — в `purpose` внутри манифеста. Бенчмарк-раннер: `research/benchmarks/document_parsing/`.

## Доступ из шагов

```python
from research.datasets.access import (
    PROCESSED_DIR,
    RAW_PDF_DIR,
    load_examples_manifest,
    load_class_attribute_sets,
    load_ground_truth,
)
```

- `PROCESSED_DIR` → `research/datasets/processed/`
- `RAW_PDF_DIR` → `data.local/input_data/pdf` (локальные PDF, gitignored)
