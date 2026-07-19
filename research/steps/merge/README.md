# Шаг: merge

## Назначение

Сборка контекстных блоков для downstream-шагов из search hits шага `retrieval`: structure chunks дополняются выбранными table chunks через placeholder-ы таблиц. Шаг не выполняет поиск и не меняет ранжирование retrieval.

## Входные данные

- Qdrant-коллекция из шага `vectorizing` — `QDRANT_COLLECTION_TEMPLATE` с `{eos_id}`.
- `research/steps/retrieval/output/{eos_id}_search.json` — список `AttributeSearchResult`.
- `research/datasets/processed/examples_manifest.json` — список `eos_id` для debug-прогона.

## Выходные данные

- `research/steps/merge/output/{eos_id}_merge.json` — список `MergeResult` (`attribute_id` + `merged_chunks`).

## `domain/`

| Модуль | Назначение |
|---|---|
| `runner.py` | `run_merge` |
| `models.py` | `MergedChunk`, `MergeResult` |
| `context_merge.py` | оркестрация: `build_merged_section`, `get_merged_chunks_for_attribute` |
| `table_stitch.py` | seam-aware stitch соседних `table_chunk_index` (`row`/`span` concat rows, `cell` склейка текста ячейки) |
| `fetch.py` | Qdrant retrieve/scroll для structure и table splits |
| `selection.py` | выбор/расширение table splits по `expansion_char_budget` |


`MergedChunk.source_point_ids` хранит canonical set Qdrant point id, включённых в контекстный блок. `display_point_id` — основной point id блока для downstream priority/display logic.

## Конфигурация

Top-level: `QDRANT_URL` (`.env`), `QDRANT_TIMEOUT` / `QDRANT_COLLECTION_TEMPLATE` (`config.yaml`).

Секция `MERGE`:

- `expansion_char_budget_structure` — бюджет расширения для structure-only hits
- `expansion_char_budget_table` — бюджет расширения для hits, где есть table chunks

## Запуск

```bash
python -m research.steps.merge.run
```

Требует выполненные шаги `vectorizing` и `retrieval`, доступный Qdrant и готовые `{eos_id}_search.json`.

## Тесты

```bash
pytest research/steps/merge/tests
```
