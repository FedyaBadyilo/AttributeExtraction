# Шаг: ocr

## Назначение

OCR и структурная разметка PDF-документов с использованием [dedoc](https://dedoc.readthedocs.io/) с кастомным пайплайном.

Шаг принимает PDF из `research/datasets/processed/examples_manifest.json`, разбирает их через dedoc с расширенными паттернами и постпроцессингом, и сохраняет полный `ParsedDocument` в JSON.

## Кастомный пайплайн dedoc

Стандартный dedoc переопределён в четырёх местах:

| Модуль | Что переопределяет | Зачем |
|---|---|---|
| `domain/patterns.py` | Паттерны классификации строк | Добавляет типы `tz_part`, `tz_subpart`, `uppercase_header`, `rule_part` для документов формата ТЗ/ТУ |
| `domain/extractor.py` | `DefaultStructureExtractor` | Четыре постпроцессинговых прохода: сплит строк `rule_part`, выравнивание уровней соседних заголовков, выравнивание заголовков-продолжений, унификация типов на одном уровне |
| `domain/tree_constructor.py` | `TreeConstructor` | Корректный сдвиг аннотаций при слиянии multiline-строк; блокировка multiline-склейки, когда строка является подписью таблицы |
| `domain/linker.py` | `LineObjectLinker` в PDF-ридерах dedoc (Txtlayer, Tabby и OCR) | Помещает `TableAnnotation` в конец строки-подписи (caption выше таблицы), а не в начало — чтобы таблица появлялась после подписи в дереве |

## Входные данные

- `research/datasets/processed/examples_manifest.json` — список документов: поля `eos_id`, `pdf_filename`.
- `data.local/input_data/pdf/<pdf_filename>` — исходные PDF-файлы (gitignored; путь = `RAW_PDF_DIR`).

Константа пути к директории с PDF: `research.datasets.access.RAW_PDF_DIR`.

**Системные зависимости:** `poppler-utils` (`pdfinfo` в PATH) и `openjdk-17-jre-headless` (`java` в PATH). См. корневой `README.md`.

## Выходные данные

`research/steps/ocr/output/{pdf_stem}.json` — полный `ParsedDocument.model_dump()` в формате dedoc API schema.

Вложения (изображения, встроенные файлы) сохраняются рядом в `output/attachments/{pdf_stem}/`.

## Конфигурация

Секция `OCR` в `config.yaml`:

```yaml
OCR:
  on_gpu: false  # true для GPU-ускорения (требует CUDA + nvidia-smi)
```

## Запуск

```bash
python -m research.steps.ocr.run
```

Прогоняет все записи из `examples_manifest.json`.

## Тесты

```bash
pytest research/steps/ocr/tests
```

