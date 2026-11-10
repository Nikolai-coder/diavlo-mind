# P10 — Requirement tracking

## Trigger
- The request contains more than three requirements, or
- requirements are spread across messages, files or attachments, or
- the user changed or added something mid-task.

## Inputs
- Every place requirements live: the request, earlier messages, attached files, linked issues, project instruction files.
- Existing behaviour that must not break.

## Protocol
1. **Extract.** Go through the sources line by line and write each requirement as its own numbered item (R1, R2, …). Keep the user's wording where it carries meaning: numbers, names, formats, limits, "must" versus "should".
2. **Classify** each item: *functional* (what it does), *constraint* (limits it must respect), *format* (shape of the output), *quality* (how good), *process* (how the work must be done).
3. **Add the implied ones** and mark them *implied*: existing tests keep passing, public names and file formats stay stable, the platform and language of the project, the language of the user.
4. **Attach a check** to each: the command, inspection or measurement that will show it is met. A requirement with no possible check is rewritten with the user until it has one.
5. **Find conflicts and gaps now.** Two requirements that cannot both hold, or a requirement that depends on a missing decision, are raised before work starts.
6. **Trace forward.** Each requirement points to the plan step or task that satisfies it. Requirements with no task and tasks with no requirement are both errors.
7. **Update on every change.** A new message that alters scope produces a ledger edit — add, modify or mark *waived by user* — never a silent mental adjustment.
8. **Walk the ledger before delivering.** Top to bottom, against the real artifact: met with evidence, unmet with reason, or not verified.

## Tools
- A ledger kept in the plan or notes; `scripts/dm_state.py req add|set|list` in long projects.
- `memory/templates/REQUIREMENTS.md` when keeping it by hand.
- Search across the conversation and files for words such as "must", "should", "never", "exactly", "at least", "format".

## Outputs
```
| ID | Requirement | Type | Check | Task | Status | Evidence |
| R1 | Export accepts --since YYYY-MM-DD | functional | CLI run | T2 | met | `export --since 2024-01-31` exit 0 |
| R2 | Invalid date exits with code 2 | functional | CLI run | T2 | met | `--since 2024-13-01` → exit 2 |
| R3 | Existing tests pass (implied) | constraint | test suite | T4 | met | 15 passed |
| R4 | README documents the flag | format | read file | T3 | unmet | not written yet |
```

## Verification
- Count the requirements in the sources and in the ledger; they match.
- Every row has a check and a status.
- No row says "met" without evidence produced in this session.
- Changed or waived rows name who decided and when.

## Recovery
- **You find a requirement you missed:** add it, assess what it invalidates, and tell the user if delivered work is affected.
- **A requirement cannot be met:** mark it *unmet*, give the reason and the nearest achievable alternative. Do not redefine it quietly.
- **Requirements conflict:** stop the affected work and ask, presenting the options and what each costs.
- **The ledger grew stale:** re-extract from the sources rather than patching from memory.
