# Dataset build

Собирает **processed**-артефакты для research-пайплайна: Excel-реестр PDF ↔ карточки изделий и ground truth в PostgreSQL → JSON/JSONL для шагов OCR → extraction → eval.

Не читает текст PDF, не вызывает LLM и не считает метрики.

Запуск требует локальной БД и `DB_*` в `.env` — в публичном demo это зона ответственности кода, а не воспроизводимый online-контур.

## Входы

1. **Excel-манифест PDF** (`--pdf-registry-path`) — какие файлы к каким карточкам относятся и с каким приоритетом.
2. **PostgreSQL** (переменные `DB_*` в `.env`) — карточки, справочник атрибутов класса, значения GT.

## Выходы (`--output-dir`, по умолчанию `research/datasets/processed/`)

| Файл | Содержание |
| --- | --- |
| `examples_manifest.json` | список примеров: id карточки, имя PDF, приоритет, class_code |
| `class_attribute_sets.json` | атрибуты по классам + флаги `for_extraction` |
| `ground_truth.jsonl` | эталонные значения `(gid, attr_id, value)` |

## Модули

| Файл | Назначение |
| --- | --- |
| `__main__.py` | CLI |
| `manifest.py` | чтение Excel-реестра |
| `nci.py` | SQL к PostgreSQL |
| `attr_details.py` | единицы измерения и allowed values |
| `rules.py` | какие атрибуты идут в extraction |
| `ground_truth.py` | нормализация пустых/диапазонных значений |
| `builder.py` | оркестрация |
| `io.py` | запись артефактов |

## Запуск

```bash
python -m research.datasets.build \
  --pdf-registry-path /path/to/pdf_files_manifest.xlsx \
  --output-dir research/datasets/processed
```

Нужны `DB_HOST`, `DB_NAME`, `DB_PORT`, `DB_LOGIN`, `DB_PASSWORD` в `.env` (см. `.env.example`).
