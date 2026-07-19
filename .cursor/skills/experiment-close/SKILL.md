---
name: experiment-close
description: Writes or updates the Conclusion and Decision sections of an experiment journal when enough evidence exists to summarize and close the experiment. Use when closing an experiment, writing `## 6. Conclusion` and `## 7. Decision`, or when the user invokes experiment close journaling.
disable-model-invocation: true
---

# Experiment Close

Use this skill when the experiment has enough evidence to be summarized and closed.

This skill owns only:

- `## 6. Conclusion`
- `## 7. Decision`

Follow [experiment-journal.mdc](../../../.cursor/rules/experiment-journal.mdc) for journal structure and invariants.

## Procedure

1. Read the experiment journal.
2. Use `## 1. Approach` and `## 2. Expected effect / hypothesis` to understand what was tested and expected.
3. Use `## 3. Runs and metrics` to understand the measured result.
4. Use `## 4. Interpretation` and `## 5. Error analysis` when available.
5. Write or update `## 6. Conclusion`.
6. Write or update `## 7. Decision`.
7. Stop.

## Conclusion focus

Summarize what became clear from the experiment.

The conclusion should answer:

- whether the expected effect was observed;
- what improved, degraded, or stayed unclear;
- what the main explanation is;
- what limitations or uncertainty remain, if important.

Do not introduce new metric analysis that is not supported by earlier sections.

## Decision focus

Write a short natural-language decision about what to do next.

The decision may describe:

- whether to keep the approach;
- whether to reject it;
- whether to run another experiment;
- whether to inspect errors or data quality further;
- whether to turn the result into the next working baseline.

## Writing guidance

Keep both sections short.

Prefer:

- `Conclusion`: one short paragraph or a few bullets;
- `Decision`: one or two sentences.

If the journal does not contain enough evidence to close the experiment, do not invent a conclusion. State what is missing instead.
