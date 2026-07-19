# Lab

Разведочные ноутбуки и разовые research-скрипты.

Код отсюда не импортируют steps, apps и eval. Переиспользуемую логику выносить в
`research/steps/<step_name>/domain/`, `research/datasets/build/` или `infra/`.

## EDA (витрина конкурса)

| Ноутбук | О чём |
| --- | --- |
| [`eda_docs.ipynb`](./eda_docs.ipynb) | Состав пилотных пакетов, реестр/комплекты, текстовый слой |
| [`eda_attrs.ipynb`](./eda_attrs.ipynb) | Справочники атрибутов, единицы, разреженность эталона |
| [`eda_units.ipynb`](./eda_units.ipynb) | Справочник единиц DMF и стыковка с `code_unit` |

Локальные данные: `NSI_DATA_ROOT` → каталог `data.local` с `input_data_ukidim` и
`input_data_handmade` (по умолчанию — соседний research-репозиторий).

## Скрипты

- `python -m research.lab.scripts.vlm_bench` — снимок page→Markdown для VLM-бенча
  E007; пишет в `research/lab/output/vlm_bench/<run_id>/` для
  `document_parsing` eval `--mode reuse`.
