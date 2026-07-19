# Extraction Eval

## Назначение

Оценка качества шага `extraction` по processed ground truth и JSON-выходам extraction. Eval считает field-agnostic labels по каждой паре `(eos_id, attr_id)`, агрегирует технические scalar metrics для MLflow и сохраняет подробные machine-readable artifacts для разбора ошибок.

## Входные данные

- `--source` — директория с extraction outputs в формате `{eos_id}_extraction.json`.
- `research/datasets/processed/examples_manifest.json` — список `eos_id` и `class_code`.
- `research/datasets/processed/class_attribute_sets.json` — список атрибутов класса; eval universe строится по `for_extraction=true`.
- `research/datasets/processed/ground_truth.jsonl` — GT rows. Для каждого `for_extraction=true` slot должен существовать GT row, иначе eval падает fail-fast.

`ground_truth.jsonl` должен хранить пустые значения как JSON `null`. Placeholder-значения вроде `-`, `-‡-`, `n/a`, `н/д` нормализуются на этапе dataset build.

## Label Rules

Base label считается по наличию GT/prediction и результату value match:

| GT | Prediction | Match | Label |
|---|---|---|---|
| пусто | пусто | true | `TN` |
| пусто | непусто | false | `FP_1` |
| непусто | пусто | false | `FN` |
| непусто | непусто | true | `TP` |
| непусто | непусто | false | `FP_2` |

Confidence хранится отдельно:

- `high_confidence=true` -> `HC`
- `high_confidence=false` или `null` -> `LC`

`error=true` prediction item считается пустым prediction с `LC` и дополнительно увеличивает metric `errors`.

## Matching

Поддерживаются deterministic comparators:

- number exact;
- range exact: GT из `ground_truth.jsonl` хранится как `[min, max]`; скалярные NCI-значения вроде `400` нормализуются на dataset build в `[400, 400]`, строки вида `0‡300` — в `[0, 300]`;
- enum exact;
- enum-list set match без учета порядка;
- string fast paths: casefold exact и edit-distance tolerance.

Для сложных string cases adapter по умолчанию использует LLM-as-judge. В offline tests judge должен быть fake/mock.

Unit matching по умолчанию выключен (`unit_matching_enabled=false`): в `rows.jsonl`
поле `unit_match` остается `null`, `is_match` считает только value match.

Включить через CLI:

```bash
python -m research.steps.extraction.eval.run \
  --source research/steps/extraction/output \
  --name extraction-eval \
  --unit-matching
```

При включении unit matching применяется **только** к атрибутам с `units` в
`class_attribute_sets`. Для остальных атрибутов `unit_match` остаётся `null`.

Сопоставление единиц:

1. deterministic normalize (NFC, `^n`/superscript → caret form, массовые синонимы вроде
   `мес`/`месяц`, варианты `°C`/`⁰C`/`℃`) — без LLM;
2. если normalize не совпал и оба unit непустые — LLM unit judge
   (`LLMUnitJudge`), по умолчанию включён вместе с `--unit-matching`
   (отключение только через `use_default_unit_judge=False` / injectable fake,
   как у string judge).

В `rows.jsonl`: `unit_match_method` (`unit_casefold_exact` /
`unit_normalized` / `unit_llm_judge` / `unit_mismatch`), `unit_judge_used`.

Требование: `ground_truth.jsonl` должен содержать поле `unit` на строках. Для
атрибутов с ЕИ при непустом GT value `gt_unit` обязан быть задан (иначе fail-fast).

## MLflow Metrics

Metrics возвращаются в приоритетном порядке:

1. `accuracy`
2. `count`
3. `errors`
4. `hc_rate`
5. `lc_rate`
6. `hc_accuracy`
7. `lc_accuracy`
8. `tp_rate`
9. `tn_rate`
10. `fp1_rate`
11. `fp2_rate`
12. `fn_rate`
13. `tp_count`
14. `tn_count`
15. `fp1_count`
16. `fp2_count`
17. `fn_count`

`accuracy = (TP + TN) / count`.

В MLflow пишутся только global scalar metrics. Per-attribute/per-eos details сохраняются artifact-ами.

## MLflow Params

Eval сохраняет только важные параметры pipeline config, которые напрямую влияют на результат extraction:

- `ATTRIBUTE_GROUPING.*` — размеры групп, similarity threshold, partition limit, LLM/embedder model keys and names;
- `CHUNKING.*` — chunk token limits and embedder;
- `VECTORIZING.*` — embedder;
- `RETRIEVAL.*` — retrieval limits, prefetch limits, batch size and embedder;
- `MERGE.*` — context expansion budgets;
- `RERANKING.*` — rerank limits, grouping thresholds and rerank LLM;
- `EXTRACTION.*` — extraction LLM, concurrency and confidence thresholds.

Системные параметры eval, например `source`, `unit_matching_enabled`,
`string_judge_enabled` и `unit_judge_enabled`, остаются в `summary.json`, но не
логируются как MLflow params.

## MLflow Dataset

Adapter логирует ground truth через `mlflow.log_input()` (`context=eval`). MLflow сам считает `digest` по содержимому `ground_truth.jsonl` — его видно в run inputs.

## Artifacts

Eval сохраняет:

- `summary.json` — основные параметры eval, включая `unit_matching_enabled`,
  `string_judge_call_count`, `unit_judge_call_count`;
- `rows.jsonl` — строка на каждый `(eos_id, attr_id)` slot с GT, prediction, match details, label и confidence;
- `errors/fp_1.json` — ложные извлечения по пустому GT;
- `errors/fp_2.json` — несовпавшие непустые значения;
- `errors/fn.json` — пропущенные непустые GT;
- `errors/technical.json` — extraction items с `error=true`.

## Запуск

```bash
python -m research.steps.extraction.eval.run \
  --source research/steps/extraction/output \
  --name extraction-eval
```

С unit matching:

```bash
python -m research.steps.extraction.eval.run \
  --source research/steps/extraction/output \
  --name extraction-eval \
  --unit-matching
```

Команда запускает общий `infra.research_eval` runner, пишет metrics/artifacts в MLflow и использует experiment name `extraction`.

## Локальная проверка без MLflow и LLM

Для smoke-check можно вызвать adapter напрямую и отключить default LLM judges:

```python
from research.steps.extraction.eval.adapter import ExtractionEvalAdapter

result = ExtractionEvalAdapter(
    use_default_string_judge=False,
    use_default_unit_judge=False,
).evaluate(
    "research/steps/extraction/output"
)
print(result.metrics)
```

## Тесты

```bash
pytest research/datasets/tests research/steps/extraction/tests
```

Тесты не должны выполнять реальные LLM, MLflow, OCR, retrieval или Qdrant вызовы.
