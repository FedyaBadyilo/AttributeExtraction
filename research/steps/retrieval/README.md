# Шаг: retrieval

## Назначение

Гибридный поиск по Qdrant-коллекции (dense + client-side BM25, RRF) для каждого атрибута класса. Шаг возвращает только search hits; сборка контекстных блоков выполняется отдельным шагом `merge`.

## Входные данные

- Qdrant-коллекция из шага `vectorizing` — `QDRANT_COLLECTION_TEMPLATE` с `{eos_id}`.
- `research/datasets/processed/class_attribute_sets.json` — атрибуты класса (`for_extraction=true`); для каждого `eos_id` берутся только атрибуты его `class_code`.
- `research/datasets/processed/examples_manifest.json` — список `eos_id` / `class_code` для debug-прогона.

Поисковый запрос строится из `attr_name`; при наличии `variant_execution_id` в manifest (берётся из записи с наибольшим `file_priority`) добавляется суффикс ` | код: <variant>`.

## Выходные данные

- `research/steps/retrieval/output/{eos_id}_search.json` — список `AttributeSearchResult` (attribute id + search hits).

## `domain/`

| Модуль | Назначение |
|---|---|
| `runner.py` | `run_retrieval` |
| `query.py` | `build_search_query` |
| `models.py` | `ChunkPayload`, `ChunkHit`, `AttributeSearchResult` |
| `search/runner.py` | hybrid Qdrant search (`search_attributes`) |

BM25-запрос — `embed_sparse_queries` из `vectorizing` (симметрично индексации). Point id — целочисленный глобальный индекс в коллекции `eos_id`; `metadata.document_chunk_index` — индекс чанка внутри PDF (`metadata.file_name`).

## Конфигурация

Top-level: `QDRANT_URL` (`.env`), `QDRANT_TIMEOUT` / `QDRANT_COLLECTION_TEMPLATE` (`config.yaml`).

Секция `RETRIEVAL`:

- `embedder_model_key` — ключ в `EMBEDDINGS`
- `embed_batch_size` — размер батча для dense/sparse embedding на документ
- `prefetch_limit_dense`, `prefetch_limit_bm25` — prefetch для RRF
- `limit` — top-K чанков на атрибут

## Запуск

```bash
python -m research.steps.retrieval.run
```

Требует выполненный шаг `vectorizing`, доступный Qdrant / embedder API и `fastembed`.

## Тесты

```bash
pytest research/steps/retrieval/tests
```
