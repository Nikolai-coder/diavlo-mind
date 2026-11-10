# P01 — Complex problem decomposition

## Trigger
- The task has more than one deliverable, or
- you cannot name the first concrete action, or
- you estimate more than about ten steps.

## Inputs
- The objective and requirement list (R1…Rn).
- What already exists: files, systems, constraints, deadlines.

## Protocol
1. Rewrite the objective as a testable outcome: "X exists and Y can be observed".
2. List the deliverables. Each deliverable is something the user can open, run or read.
3. Split each deliverable into **units**. A unit is finished when one check passes. If you cannot write the check, the unit is still too vague — split again, or turn it into a research unit whose output is an answer.
4. For every unit write one line: `id · output · check · depends on · requirements covered`.
5. Stop splitting when a unit fits one focused block of work: about one file, one function group, one document section, or one experiment.
6. Order the units: dependencies first; among the rest, the one most likely to invalidate the plan goes first. Prefer a thin end-to-end slice over finishing one layer completely.
7. Mark units that can run in parallel: they must not write the same file or depend on each other's output.
8. Check coverage both ways: every requirement appears in at least one unit; every unit serves at least one requirement or is removed.

## Tools
- A notes file or task tracker to hold the unit list (`scripts/dm_state.py task add` in AUTONOMOUS mode).
- File listing and search to confirm what already exists before creating units for it.

## Outputs
An ordered unit list, for example:

```
T1 · parser for config v2 · unit tests for 6 sample files pass · — · R1, R2
T2 · migration command · dry-run on fixture prints 3 planned changes · T1 · R3
T3 · docs page · renders, commands copy-paste clean · T2 · R4
```

## Verification
- Every unit has exactly one owner and one check.
- No dependency cycle; no unit depends on a later one.
- Requirement coverage is complete in both directions.
- The first unit can start now with what you have.

## Recovery
- A unit turns out bigger than expected: split it in place, keep its id as a parent, re-check coverage.
- A hidden dependency appears: add it as its own unit before the one that needs it; do not smuggle it into the current unit.
- The decomposition no longer matches reality: stop, rewrite the list, tell the user what changed and why. Continuing with a stale list is the failure, not the re-plan.
