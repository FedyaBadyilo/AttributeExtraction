# Шаг: vectorizing

## Назначение

Индексация чанков из шага `chunking` в Qdrant: dense-эмбеддинги (embedder API) + sparse BM25. Одна коллекция на `eos_id`; при повторном запуске коллекция пересоздаётся.

## Входные данные

- `research/steps/chunking/output/{pdf_stem}.json` — `ChunkedDocument`.
- `research/datasets/processed/examples_manifest.json` — список PDF для выбора артефактов и группировки по `eos_id`.

Индексируется пересечение манифеста и chunking-артефактов: лишние файлы в `chunking/output/` без записи в манифесте игнорируются; отсутствующий артефакт для записи манифеста — ошибка.

## Выходные данные

Точки в Qdrant, коллекция `QDRANT_COLLECTION_TEMPLATE` с подстановкой `{eos_id}`.

Payload на точку:

| Поле | Источник |
|---|---|
| `content` | `chunk.content` (без prefix для embedding) |
| `metadata` | поля `chunk.metadata` (`file_name`, `document_chunk_index`, `header_path`, …) |

Point id — глобальный порядковый индекс `0…N-1` в коллекции `eos_id` (порядок PDF из манифеста, затем document order внутри каждого файла).

`eos_id` задаётся коллекцией; `file_priority` и прочие поля манифеста — join при retrieval по `file_name`.

Текст для dense/BM25: `prepare_content_for_indexing` — strip markdown + prefix `header_path`.

## `domain/`

| Модуль | Назначение |
|---|---|
| `runner.py` | оркестрация: `index_chunks` |
| `prepare.py` | текст для dense/BM25 |
| `dense_embed.py` | dense-эмбеддинги через `get_openai_embeddings` |
| `sparse_embed.py` | BM25: `embed_sparse_documents` (index), `embed_sparse_queries` (retrieval), `language=russian` |
| `collection.py` | создание hybrid-коллекции (`recreate=True` по умолчанию) |
| `points.py` | payload и `PointStruct` |
| `upsert.py` | upload в Qdrant |

## Конфигурация

Top-level:

- `QDRANT_URL` (`.env`), `QDRANT_TIMEOUT` (`config.yaml`)
- `QDRANT_COLLECTION_TEMPLATE` — например `AttributeExtraction-{eos_id}`

Секция `VECTORIZING`:

- `embedder_model_key` — ключ в `EMBEDDINGS`

## Запуск

```bash
python -m research.steps.vectorizing.run
```

Требует выполненный шаг `chunking`, доступный Qdrant / embedder API и `fastembed` (BM25 считается локально — серверу Qdrant InferenceService не нужен).

## Тесты

```bash
pytest research/steps/vectorizing/tests
```
