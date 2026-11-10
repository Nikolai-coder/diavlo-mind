# Example 02 — hybrid setup through the orchestrator

**What was run.** `scripts/dm_orchestrate.py` on 2026-11-10 with two different models: `fable` as advisor (planner and reviewer) and `claude-haiku-4-5` as executor, both reached through the local Claude Code CLI with tools disabled (`claude-cli` provider), so each call is a plain text completion.

```bash
cp -r ../01-claude-code-skill/project-before /tmp/demo2
python scripts/dm_orchestrate.py \
  --task examples/01-claude-code-skill/task.md --workspace /tmp/demo2 --mode standard \
  --advisor claude-cli:fable --executor claude-cli:claude-haiku-4-5 \
  --check-cmd "python3 -m unittest discover -s tests"
```

The executor has no tools. It returned three complete files between marker lines; the orchestrator wrote them into the workspace and ran the check command itself.

## What happened

| Step | Model | Input tokens | Output tokens | Reported cost | Seconds |
|---|---|---|---|---|---|
| Plan: 9 requirements (3 marked implied), 1 task, 6 assumptions | fable | 15,598 | 3,972 | $0.408 | 36 |
| Execute: `export.py`, `tests/test_export.py`, `README.md` | claude-haiku-4-5 | 33,009 | 9,442 | $0.087 | 61 |
| Check: `python3 -m unittest discover -s tests` → exit 0 | orchestrator | — | — | — | — |
| Review: verdict PASS, 1 minor finding, 3 notes | fable | 17,108 | 2,791 | $0.220 | 28 |

Status DONE, no repairs, no escalation, 125 s in total, $0.715 reported.

Files: `plan.json` (the planner's output), `review.json` (the reviewer's findings), `report.md` (the generated report), `summary.json`, `calls.json` (sizes and usage per call), `project-after/` (the resulting project).

In `report.md` the acceptance check is marked VERIFIED because the orchestrator executed it. The per-requirement rows are marked SOURCED: they come from the reviewer reading the files, and the report says so.

## Independent check

Run afterwards on `project-after/`: 11 tests pass; `--since 2024-02-01` prints the three later orders; `--since 2024-13-01` prints `invalid date '2024-13-01': expected YYYY-MM-DD` and exits with code 2.

## What the numbers say

The advisor's two calls cost about seven times the executor's work. On a task this small, a single small-model session with the skill (example 01, $0.014) did the same job for about one fiftieth of the cost. The hybrid setup is for work the executor cannot plan or review reliably on its own; this run shows the mechanism working, not a saving. Whether it pays off for your tasks is a question for `evaluation/`.
