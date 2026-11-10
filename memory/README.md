# memory/ — project-state templates and schemas

This folder holds **empty structures**, not memories. Nothing here records facts about any user or past project. The templates define what a project should write down so that work survives a lost context, a new session or a handover.

## Where state lives

In the user's project, never in this skill's folder:

```
<project>/.diavlo-mind/
├── state.json        machine-readable state, written by scripts/dm_state.py
├── STATE.md          human-readable snapshot (dm_state.py report)
├── CONVENTIONS.md    rules every contributor follows
├── DECISIONS.md      longer decision records
├── FAILURE_LOG.md    failures and what was learned
└── runs/             transcripts written by scripts/dm_orchestrate.py
```

## Templates

| Template | Use it for | Procedure |
|---|---|---|
| `templates/STATE.md` | The single snapshot of objective, requirements, tasks, decisions, last checkpoint | `workflows/modes/autonomous.md` |
| `templates/REQUIREMENTS.md` | The requirement ledger | `workflows/procedures/p10-requirement-tracking.md` |
| `templates/PLAN.md` | Milestones and tasks | `workflows/procedures/p02-long-horizon-planning.md` |
| `templates/DECISIONS.md` | Decision log | `workflows/procedures/p14-tradeoff-analysis.md` |
| `templates/CHECKPOINT.md` | What a fresh session needs to continue | `workflows/protocols/recovery.md` |
| `templates/PROGRESS_REPORT.md` | Milestone report for the user | `workflows/modes/autonomous.md` |
| `templates/HANDOFF.md` | Passing work to another agent or person | `workflows/protocols/recovery.md` |
| `templates/FAILURE_LOG.md` | Failures and their cause category | `workflows/protocols/self-improvement.md` |
| `templates/CONVENTIONS.md` | Names, structure, style, interfaces, glossary | `workflows/procedures/p20-consistency-at-scale.md` |

Copy a template into `.diavlo-mind/` and replace the `<…>` fields. Delete rows you do not need.

## Schemas

| Schema | Describes | Checked by |
|---|---|---|
| `schemas/state.schema.json` | `.diavlo-mind/state.json` | `scripts/dm_state.py validate` |
| `schemas/task-packet.schema.json` | A delegation in JSON form | `scripts/dm_packet.py validate` |
| `schemas/result-packet.schema.json` | A return in JSON form | `scripts/dm_packet.py validate` |

The scripts use a small built-in validator (`scripts/dm_schema.py`) so they need no third-party package. The schemas are standard JSON Schema (draft 2020-12) and also work with any external validator.

## With and without scripts

**With Python 3.9+:**

```
python scripts/dm_state.py init --objective "Ship the export filter" --mode autonomous --done "pytest -q passes"
python scripts/dm_state.py req add "Export accepts --since YYYY-MM-DD"
python scripts/dm_state.py task add "Parse and validate --since" --req R1 --accept "pytest tests/test_export.py -q"
python scripts/dm_state.py next
python scripts/dm_state.py task set T1 --status done --evidence "pytest → 6 passed"
python scripts/dm_state.py checkpoint "T1 done" --next "T2: apply filter"
python scripts/dm_state.py report
python scripts/dm_state.py resume
python scripts/dm_state.py done-check
```

Add `--dir <project>` when running from outside the project.

**Without Python:** keep `STATE.md` by hand from the template. The discipline is the same: update it when something changes, write a checkpoint before stopping, and trust the files over the notes when they disagree.

## What does not belong here

- Personal data, credentials or secrets.
- Invented history. A template field that has no real value stays empty.
- Conversation transcripts. Record decisions and evidence, not chatter.
