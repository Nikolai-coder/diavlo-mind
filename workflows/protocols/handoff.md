# Handoff protocol — task packets and result packets

Every delegation is a **task packet**. Every return is a **result packet**. The receiving agent starts with no memory of your conversation: whatever is not in the packet does not exist for it.

Packets are plain text and work on any model. A JSON form with the same fields exists for scripts: schemas in `memory/schemas/`, helper `scripts/dm_packet.py`.

## Task packet

```
TASK PACKET
id: T7
role: executor
mode: STANDARD
objective: The export command accepts --since YYYY-MM-DD and omits older rows.
context:
  - CLI entry point is src/export.py, function main() (read it first)
  - Dates in the data are ISO strings in UTC (data/README.md)
requirements:
  - R1: --since accepts YYYY-MM-DD
  - R2: rows older than the date are excluded
  - R3: an invalid date prints a clear error and exits with code 2
constraints:
  - may write: src/export.py, tests/test_export.py
  - read-only: everything else
  - no new dependencies
inputs:
  - tests/fixtures/sample.csv
deliverable: The code change and tests, plus a result packet.
acceptance:
  - python -m pytest tests/test_export.py -q passes
  - python src/export.py --since 2024-13-01 exits with code 2
escalate_if:
  - the date format in the data is not ISO
  - the change needs a file outside "may write"
budget: about 25 tool calls
```

### Field rules

| Field | Rule |
|---|---|
| `id` | Same id as the task in project state. |
| `role` | One of: architect, planner, executor, researcher, reviewer, validator, optimizer, orchestrator. |
| `mode` | FAST, STANDARD, DEEP or AUTONOMOUS — tells the agent how much ceremony is expected. |
| `objective` | One sentence describing the outcome, not the activity. |
| `context` | Only facts and pointers the agent needs, each with where it came from. No history. |
| `requirements` | Ids and text copied from the ledger, never paraphrased from memory. |
| `constraints` | What may be written, what is read-only, and any other limit. Writable paths are mandatory for executors and optimizers. |
| `inputs` | Files, data or earlier results to start from. |
| `deliverable` | Exactly what to hand back and in what form. |
| `acceptance` | Checks that define done. Each can be run or inspected. |
| `escalate_if` | Conditions under which the agent must stop and return BLOCKED. |
| `budget` | Optional limit on calls, time or tokens. |

Before sending, read the packet as a stranger would. If you could not act on it, it is not ready.

**Reviewers and validators** get the requirements and the artifact only. Leave out the author's reasoning, self-assessment and reported test results — independence is the point (`workflows/procedures/p19-independent-verification.md`).

## Result packet

```
RESULT PACKET
id: T7
role: executor
status: DONE
summary: Added --since parsing and filtering in export.py with 3 new tests.
deliverables:
  - src/export.py
  - tests/test_export.py
evidence:
  - R1: met — VERIFIED — `export.py --since 2024-01-31` exit 0, 41 rows
  - R2: met — VERIFIED — test_since_excludes_older passes
  - R3: met — VERIFIED — `--since 2024-13-01` → "invalid date", exit 2
changes:
  - src/export.py (modified)
  - tests/test_export.py (modified)
issues:
  - minor — README.md — flag not documented — add to usage section (outside my writable paths)
assumptions:
  - --since is inclusive of the given date
open_questions:
  - none
next: Planner task T8 (README) can start.
```

### Field rules

| Field | Rule |
|---|---|
| `status` | DONE (all acceptance checks VERIFIED), PARTIAL, BLOCKED or FAILED. |
| `summary` | At most five lines. Outcome first. |
| `deliverables` | Paths, or the content itself when there are no files. |
| `evidence` | One line per requirement: `met`, `unmet` or `not_verified`; level VERIFIED, SOURCED, ASSUMED or UNKNOWN; the proof. |
| `changes` | Every file created, modified or deleted. |
| `issues` | Severity (blocker, major, minor, note), where, what, suggested fix. Includes things noticed outside the task. |
| `assumptions` | Anything decided without confirmation. |
| `open_questions` | What the orchestrator must answer. |
| `next` | The recommended next action. |

## Rules for the sender

1. One packet, one unit of work, one owner.
2. Freeze shared interfaces before sending packets that depend on them.
3. Never send two packets that may write the same file.
4. A packet without acceptance checks is not sent.

## Rules for the receiver

1. Missing or contradictory fields: return BLOCKED naming the field. Do not guess the objective.
2. Stay inside `constraints`. Needing more is an `escalate_if` condition, not a judgment call.
3. Return a result packet even when you fail. A clear FAILED with evidence is useful; silence or a vague success is not.
4. Do not start work that belongs to another packet.

## Rules for the integrator

1. A result packet is a claim. Re-run the acceptance checks before marking the task done.
2. Copy `issues`, `assumptions` and `open_questions` into project state; they are easily lost.
3. PARTIAL and BLOCKED go back into the queue with a corrected packet, not into your own context to be finished silently.

## JSON form

```json
{
  "type": "task",
  "id": "T7",
  "role": "executor",
  "mode": "STANDARD",
  "objective": "The export command accepts --since YYYY-MM-DD and omits older rows.",
  "context": ["CLI entry point is src/export.py"],
  "requirements": [{"id": "R1", "text": "--since accepts YYYY-MM-DD"}],
  "constraints": {"may_write": ["src/export.py"], "read_only": ["*"], "other": ["no new dependencies"]},
  "inputs": ["tests/fixtures/sample.csv"],
  "deliverable": "Code change and tests, plus a result packet.",
  "acceptance": ["python -m pytest tests/test_export.py -q passes"],
  "escalate_if": ["the date format in the data is not ISO"]
}
```

```
python scripts/dm_packet.py new task --id T7 --role executor --objective "..."   # template
python scripts/dm_packet.py validate packet.json                                  # check fields
python scripts/dm_packet.py render packet.json                                    # text form for a prompt
```
