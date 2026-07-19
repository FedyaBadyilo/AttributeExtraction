# Context Rebuild

Builds the final extraction context after context grouping.

## Inputs

- `research/steps/context_grouping/output/{eos_id}_attribute_groups.json`
- `research/steps/reranking/output/{eos_id}_rerank.json`
- `research/steps/merge/output/{eos_id}_merge.json`
- Qdrant collection for the `eos_id`

## Output

- `research/steps/context_rebuild/output/{eos_id}_extraction_context.json`

The output validates as `GroupedContextResult` and is consumed by extraction.

## Run

```bash
python -m research.steps.context_rebuild.run
```
