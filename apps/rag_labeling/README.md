# RAG labeling

Полуавтоматическая разметка датасета для оценки RAG: для каждого атрибута показываются кандидаты из гибридного поиска (dense + BM25). Выбор чанка по `point_id`, «Нет в документе» или ручной ввод `point_id`.

## Запуск

Из **корня проекта**:

```bash
streamlit run apps/rag_labeling/app.py
```

Зависимости: `streamlit`, `diskcache` (плюс зависимости шагов `ocr`, `retrieval`, `vectorizing`).

## Конфиг и данные

- **config.yaml**: `EMBEDDINGS.base_embedder`, `RETRIEVAL`, `QDRANT_TIMEOUT`, `OCR`
- **`.env`**: `QDRANT_URL` (+ LLM/embeddings vars)
- **Манифест:** `research/datasets/processed/examples_manifest.json`
- **Ground truth:** `research/datasets/processed/ground_truth.jsonl`
- **Атрибуты класса:** `research/datasets/processed/class_attribute_sets.json`
- **PDF:** `data.local/input_data/pdf/` (`RAW_PDF_DIR` в `research/datasets/access.py`)
- **Метки:** diskcache в `apps/rag_labeling/.cache/rag_labels`
- **Экспорт:** `research/datasets/processed/rag_labels/{eos_id}.json`

Шаблон Qdrant-коллекции для разметки: `RAG-Labeling-{eos_id}` (задаётся в `pipeline.py`).

## Логика

- Документ = `eos_id` (все PDF из манифеста с этим id объединяются).
- Задачи разметки: атрибуты с `for_extraction=true`, непустым ground truth (без `-`, `null` и т.п.).
- При первом запросе кандидатов для `eos_id` запускается on-demand пайплайн: OCR → markdown_formatting → chunking → vectorizing.
- Факт индексации кэшируется в `apps/rag_labeling/.cache/rag_pipeline/indexed.json`.
- Поиск: `build_search_query` + суффикс `| эталон: {value}`; top-10 сырых hybrid hits.
- Метка хранит Qdrant `point_id` (int, `0..N-1` в коллекции документа).

## Сброс кэша пайплайна

Если изменили шаги OCR / markdown_formatting / chunking / vectorizing, удалите `apps/rag_labeling/.cache/rag_pipeline`, чтобы при следующем запуске индексация выполнилась заново.

## Формат экспорта

```json
[
  {"attr_id": "attr10332", "target_point_id": 42},
  {"attr_id": "attr10333", "target_point_id": null}
]
```
