---
name: experiment-metrics
description: Updates the Runs and metrics and Interpretation sections of an experiment journal from explicit run IDs, MLflow MCP, evaluation artifacts, or eval command output. Use after evaluation completes, when run-level metrics are available, or when the user invokes experiment metrics journaling.
disable-model-invocation: true
---

# Experiment Metrics

Use this skill after evaluation has been completed and run-level metrics or artifacts are available.

This skill owns only:

- `## 3. Runs and metrics`
- `## 4. Interpretation`

Follow [experiment-journal.mdc](../../../.cursor/rules/experiment-journal.mdc) for journal structure and invariants.

This skill has two phases:

1. **Metrics capture** — factual summary of relevant runs and metrics.
2. **Metrics analysis** — metric-level analysis of what the observed values suggest.

Do not perform error analysis, write final conclusions, or make decisions in this skill.

## Source resolution

If the user gave an explicit `run_id` pointer, use it. Otherwise resolve runs and metrics via MLflow MCP when it is available.

Use other context already in the chat or journal only when it actually lets you read metrics.

Do not guess run IDs or metric values. If metrics cannot be read and MLflow MCP is not connected or unavailable, stop without editing the journal and tell the user what is missing.

Use the latest MLflow run only when the user explicitly asks to use the latest run.

## Procedure

1. Read the experiment journal.
2. Use `## 1. Approach` and `## 2. Expected effect / hypothesis` to understand what was tested and which metrics matter.
3. Resolve the relevant run source.
4. Match each relevant run to the corresponding approach, variant, or tested configuration.
5. Select only metrics that are relevant for the experiment.
6. Write or update `## 3. Runs and metrics` with factual run and metric information.
7. Analyze the selected metrics at metric level.
8. Separate metric-supported observations from explanations that require additional evidence.
9. Write or update `## 4. Interpretation`.
10. Stop.

## Phase 1 — Runs and metrics

Update `## 3. Runs and metrics` with a compact summary of relevant runs and metrics.

Each run must be identifiable by `run_id`.

### Metric selection

Focus on **technical metrics** recorded in MLflow runs — eval scores, counts, latencies, and other logged numeric values. Do not substitute qualitative judgments, error patterns, or conclusions here.

Do not copy all available MLflow metrics.

Include only:

- metrics targeted by the hypothesis;
- metrics needed to understand trade-offs;
- metrics that changed unexpectedly;
- metrics needed to support later interpretation.

Derived metrics are allowed only when they can be computed directly from logged metrics. Show the formula and source values.

If an expected metric is not logged and cannot be derived from scalar metrics, list it as missing instead of estimating it.

If a metric did not change and is not important for the experiment, omit it.

### Metrics writing guidance

Prefer a compact table when there are several runs or variants.

A typical table may include:

| Approach / variant | MLflow run_id | Key difference | Relevant metrics | Notes |
| ------------------ | ------------- | -------------- | ---------------- | ----- |
| ...                | `...`         | ...            | ...              | ...   |

Adapt the columns to the experiment. Do not force this exact table if another format is clearer.

Keep notes factual: run name, status, commit, source, or artifact availability.

Do not describe error causes, quality meaning, or final interpretation in `## 3. Runs and metrics`.

If the run-to-variant mapping is unclear, infer it from run params, tags, names, or supplied context. If it remains ambiguous, mark the ambiguity in the section instead of inventing a confident mapping.

## Phase 2 — Interpretation

Treat `## 4. Interpretation` as **metric-level analysis**, not final conclusion.

Explain what the observed metrics suggest, and clearly separate:

- directly observed metric values;
- derived observations based on those metrics;
- plausible explanations that require further analysis;
- missing checks or unavailable measurements.

Connect the result back to the expected effect:

- whether the expected metric-level effect appeared;
- whether the direction of change is consistent with the hypothesis;
- whether there are meaningful trade-offs;
- whether any metric changed unexpectedly;
- whether the available measurements are sufficient for a primary interpretation;
- whether additional analysis is needed before conclusion.

Do not simply restate the metric table.

Do not introduce new metrics, formulas, or derived calculations only in `## 4. Interpretation`. If a derived metric is needed for interpretation, include it first in `## 3. Runs and metrics` with formula and source values.

Do not claim causal mechanisms from aggregate metrics alone. Aggregate metrics may indicate patterns or shifts, but underlying causes remain hypotheses until validated with more detailed analysis or supporting artifacts.

Be careful when interpreting aggregate metrics over heterogeneous data. Do not make strong claims about a specific subset, failure mode, or behavioral mechanism unless the relevant slice or supporting evidence is available.

If an expected metric is missing or cannot be derived from available values, state that it cannot be checked yet and mention what kind of measurement or artifact would be needed.

### Interpretation writing guidance

Write concise research analysis.

Do not explain every metric mechanically. Focus on the metrics that are relevant to the hypothesis, trade-offs, unexpected changes, or missing checks.

Prefer a few short paragraphs or bullets. Use a table only if it makes the reasoning clearer.

Use cautious wording for explanations that are not directly proven by the metrics: "may indicate", "suggests", "needs checking", "requires additional analysis".

Avoid final decision language here. Final conclusions and next actions belong to `## 6. Conclusion` and `## 7. Decision`.

If multiple variants were tested, compare them directly by the relevant metrics and trade-offs.

If the metrics are insufficient for interpretation, say so explicitly in `## 4. Interpretation` and explain what is missing.

If the result suggests a need for additional analysis, mention the specific direction to check, but do not perform that analysis in this skill.

End the interpretation with the current interpretation status: what is already clear from metrics, what remains uncertain, and what should be checked next if needed.
