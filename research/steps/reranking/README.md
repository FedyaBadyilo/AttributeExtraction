# Reranking

Scores merged chunks for each attribute with the LLM reranker.

## Inputs

- `research/steps/merge/output/{eos_id}_merge.json`
- `research/steps/retrieval/output/{eos_id}_search.json`
- processed class attributes from `research/datasets/processed/`

## Output

- `research/steps/reranking/output/{eos_id}_rerank.json`

The output is a JSON array of `RerankAttribute`. This step does not perform context grouping, Jaccard merging, or Qdrant context rebuild.

## Run

```bash
python -m research.steps.reranking.run
```
