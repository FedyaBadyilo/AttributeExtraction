# Context Grouping

Builds per-`eos_id` attribute groups for extraction context from rerank evidence.

## Inputs

- `research/steps/reranking/output/{eos_id}_rerank.json`
- `research/steps/attribute_grouping/output/attribute_groups.json` (ключ — `class_code`)
- processed class attributes from `research/datasets/processed/`

## Output

- `research/steps/context_grouping/output/{eos_id}_attribute_groups.json`

The output validates as `AttributeGroups`. This step does not carry chunk payloads, rerank scores, or Qdrant-rebuilt context forward.

## Run

```bash
python -m research.steps.context_grouping.run
```
