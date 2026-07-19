---
name: experiment-error-analysis
description: Writes or updates the Error analysis section of an experiment journal from error artifacts, eval outputs, or MLflow runs. Use when metrics have been interpreted and task-specific error analysis is needed, or when the user invokes experiment error analysis journaling.
disable-model-invocation: true
---

# Experiment Error Analysis

Use this skill when metrics have been interpreted and the experiment needs a task-specific analysis of errors or changed cases.

This skill owns only:

- `## 5. Error analysis`

Follow [experiment-journal.mdc](../../../.cursor/rules/experiment-journal.mdc) for journal structure and invariants.

## Source resolution

Use the first available reliable source:

1. Error artifacts or paths provided by the user.
2. Error artifacts referenced in MLflow runs from `## 3. Runs and metrics`.
3. Supplied files, eval reports, exported tables, or notebook outputs.
4. MLflow MCP search only when run IDs or concrete filters are available.

Do not guess error artifact locations. If no reliable source is available, stop and ask for the error artifact, run ID, or path.

## Procedure

1. Read the experiment journal.
2. Use `## 4. Interpretation` to understand what needs explanation.
3. Resolve relevant error artifacts or diagnostic data.
4. Analyze only the errors needed to explain the observed metrics or support the next decision.
5. Write or update `## 5. Error analysis`.
6. Stop.

## Analysis focus

Choose the analysis form based on the experiment.

Possible directions include:

- changed labels or prediction classes;
- representative failed cases;
- dominant error groups;
- GT issues;
- hallucinations;
- retrieval misses;
- extraction or postprocessing errors;
- document-level, class-level, attribute-level, or query-level patterns;
- regressions introduced by a specific variant;
- cases where metrics improved but behavior became worse.

Do not force a universal error taxonomy or table.

## Writing guidance

Keep the analysis practical and selective.

Prefer explaining the few error patterns that matter most for the experiment over listing every failure.

Use examples when they clarify the failure mode.

If error analysis changes the earlier interpretation, mention that explicitly inside this section.

If the available artifacts are insufficient for meaningful error analysis, state what is missing and what should be checked next.
