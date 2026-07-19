# Шаг: markdown_formatting

## Назначение

Детерминированное преобразование выхода dedoc (`ParsedDocument`) в компактный markdown-артефакт для downstream-шагов.

Шаг принимает JSON из `research/steps/ocr/output/`, обходит дерево структуры и таблицы независимо, и сохраняет `FormattedDocument` в JSON.

## Что делает

| Ветка | Вход | Выход |
|---|---|---|
| structure | `content.structure` (дерево dedoc) | дерево `FormattedNode` с markdown-текстом узлов, упрощёнными метаданными и плейсхолдерами таблиц/вложений |
| tables | `content.tables` | список `FormattedTable` (uid + markdown) |

Обработка аннотаций узлов: bold, italic, linked_text (replace), table и attach (inject).

## Входные данные

- `research/steps/ocr/output/{pdf_stem}.json` — `ParsedDocument` из шага `ocr`.
- Список документов берётся из `research/datasets/processed/examples_manifest.json` (как в `ocr`).

## Выходные данные

`research/steps/markdown_formatting/output/{pdf_stem}.json` — `FormattedDocument.model_dump()`.

## Запуск

```bash
python -m research.steps.markdown_formatting.run
```

Прогоняет все записи из `examples_manifest.json`. Требует предварительно выполненный шаг `ocr`.

## Тесты

```bash
pytest research/steps/markdown_formatting/tests
```
