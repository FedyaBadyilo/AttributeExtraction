# Шаг: chunking

## Назначение

Детерминированное разбиение `FormattedDocument` (выход шага `markdown_formatting`) на чанки для retrieval и downstream-шагов.

Структурный текст и таблицы эмитятся отдельно: один structure-чанк на накопленный фрагмент тела и отдельный table-чанк на каждую таблицу. Длинные чанки делятся по лимиту токенов embedder-модели (локальный HuggingFace tokenizer, совпадающий с API-эмбеддером).

Таблицы режутся каскадом: rowspan-safe по строкам → mid-span внутри oversized-атома → mid-cell по тексту самой длинной ячейки → mid-cols по stream ячеек, если каркас строки шире budget. Между соседними сплитами в metadata пишется `seam_to_next` (`row` / `span` / `cell` / `cols`), чтобы шаг merge мог собрать исходный HTML, не меняя retrieval.

## Что делает

| Уровень | Поля |
|---|---|
| `ChunkedDocument` (корень, per PDF) | `eos_id`, `pdf_filename`, `chunks` |
| `Chunk` | `content`, `metadata` |
| chunk metadata (base) | `document_chunk_index`, `file_name`, `header_path`, `chunk_type` |
| structure chunk metadata | `page_numbers`, `table_uids` |
| table chunk metadata | `table_uid`, `table_chunk_index`, `seam_to_next` |


`file_priority` и прочие поля манифеста в артефакт не входят — join по `eos_id` + `pdf_filename` на шаге vectorizing.

## Входные данные

- `research/steps/markdown_formatting/output/{pdf_stem}.json` — `FormattedDocument`.
- Список документов — `research/datasets/processed/examples_manifest.json`.

## Выходные данные

`research/steps/chunking/output/{pdf_stem}.json` — `ChunkedDocument.model_dump()` (один JSON на PDF).

## Конфигурация

Секция `CHUNKING` в `config.yaml`:

- `max_chunk_tokens` — верхний лимит токенов на чанк (split при превышении);
- `min_chunk_tokens` — минимальный размер буфера перед emit на body (`0` = emit сразу);
- `embedder_model_key` — ключ в `EMBEDDINGS`; поле `model` задаёт HuggingFace tokenizer для подсчёта токенов.

## Запуск

```bash
python -m research.steps.chunking.run
```

Требует предварительно выполненный шаг `markdown_formatting`.

## Тесты

```bash
pytest research/steps/chunking/tests
```
