---
name: experiment-start
description: Creates or updates experiment journal approach and hypothesis sections at the approach-definition stage. Use when defining a new experiment approach, writing `## 1. Approach` and `## 2. Expected effect / hypothesis`, updating an existing experiment journal before runs, or when the user invokes experiment approach journaling.
---

# Experiment Start

Use this skill to create a new experiment journal or update an existing one at the approach-definition stage.

This skill owns only:

- `## 1. Approach`
- `## 2. Expected effect / hypothesis`

Follow [experiment-journal.mdc](../../../.cursor/rules/experiment-journal.mdc) for the journal structure and invariants.

## Output

If an existing experiment journal is referenced, update its approach-oriented sections.

If no existing journal is referenced, create a new journal with the standard section structure and fill only:

- `## 1. Approach`
- `## 2. Expected effect / hypothesis`

Leave later sections empty.

## Procedure

1. Determine whether to create a new journal or update an existing one.
2. Analyze the supplied context.
3. Identify whether the experiment is a baseline, a single change, or a group of close variants.
4. Separate research-relevant content from repository mechanics, debug workflow, and implementation details.
5. Write or update `## 1. Approach`.
6. Write or update `## 2. Expected effect / hypothesis`.
7. Stop.

## Writing guidance

- Write at the **research approach level**, not at the repository mechanics level.
- For a **baseline**, describe the measured pipeline or evaluated chain enough to make future comparisons understandable.
- For a **non-baseline** experiment, focus on the meaningful change rather than repeating the full baseline.
- If several close variants belong to the same idea, keep them in the same journal and describe them as variants.
- Use repo context to understand the approach, but do not mirror repo structure into the journal.
- Prefer conceptual component names over file names, function names, variable names, and internal artifact names.
- Mention technical identifiers only when they are necessary for understanding the experiment: model names, known tools, key parameters, metric names, run IDs, or important configuration values.
- Do not include run commands, debug instructions, detailed data-build flow, or eval implementation details unless the experiment specifically changes those parts.
- For dataset context, describe the evaluated scope and assumptions, not the full data preparation procedure.
- For eval context, describe what is measured and why, not the internal comparator implementation, unless the experiment changes evaluation logic.

Use prose, bullets, small tables, or Mermaid diagrams when useful. Do not turn the journal into a low-level implementation changelog.

If the user says the approach has already been implemented, or asks to synchronize the journal with actual changes, inspect the relevant `git diff` or changed files when the supplied context is insufficient. Use the diff to infer the actual approach, not to list changed files.
