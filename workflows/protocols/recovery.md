# Recovery protocol — resuming interrupted work

Use this when a session starts with work already in progress: after a crash, a context reset, a handover from another agent or person, or simply the next day.

The rule behind every step: **the files are the truth; notes are a claim about the files; memory is neither.**

## 1. Find the state

Look, in this order:

1. `.diavlo-mind/state.json` and `.diavlo-mind/STATE.md` in the project root.
2. Handoff or notes files: `HANDOFF.md`, `NOTES.md`, `PROGRESS.md`, `TODO.md`, a plan file.
3. Version control: `git status`, `git log --oneline -15`, `git stash list`, uncommitted diff.
4. The original request and requirement list, wherever they were given.

If `dm_state.py` is available:

```
python scripts/dm_state.py resume --dir <project>
```

It prints the objective, mode, definition of done, last checkpoint, tasks in progress, tasks ready to start, blocked tasks and open questions.

## 2. Verify the state against reality

Do not act on the snapshot until these are checked:

| Claim in the state | How to verify |
|---|---|
| Task T is `done` | Its acceptance check still passes now. |
| Task T is `doing` | Inspect its files: finished, half-done, or untouched? |
| "Tests pass" | Run them. |
| Files listed as created | They exist and are non-empty. |
| Last checkpoint's "next action" | Still makes sense given what the files show. |

Run the project's baseline checks once and record the result. This is the new starting point.

## 3. Reconcile

- A task marked `done` whose check fails → set back to `todo` with a note. Report it.
- A task marked `doing`:
  - work complete and check passes → `done` with evidence;
  - work partial and coherent → continue it;
  - work partial and unclear → revert that task's files to the last known good state, set `todo`.
- Files changed that no task accounts for → identify them from the diff; either attach them to a task or flag them to the user. Do not delete unexplained work.
- Notes that contradict files → correct the notes and write down the discrepancy.

## 4. Re-anchor

Before the first new action, restate in a few lines:

- the objective and definition of done,
- what is verified complete,
- what is in progress,
- the next action and its check.

If this cannot be written clearly, the state is not yet understood — return to step 2.

## 5. Continue

Resume the normal loop for the current mode (`workflows/modes/`). Write a checkpoint immediately after the first completed task, so the recovery itself is recorded:

```
python scripts/dm_state.py checkpoint "Resumed: verified T1–T6, reset T7" --next "T7: implement filter"
```

## Leaving work resumable

Recovery is only as good as what the previous session left. Before stopping for any reason:

1. Bring the workspace to a coherent point: finish or revert the current small step.
2. Update task statuses with evidence.
3. Write a checkpoint: what changed, what is in progress, the next action, open questions, exact commands to verify the current state.
4. Make sure the next action is something a stranger could start on with only the files.

A good checkpoint answers: *What is done and how do I confirm it? What was I in the middle of? What do I do next? What do I not know yet?*

## When there is no state at all

1. Reconstruct from artifacts: version control history, file timestamps, test results, the diff against the last commit.
2. Re-derive the requirement list from the original request.
3. Compare the artifact with the requirements to estimate what is done; verify by running checks, not by reading.
4. Tell the user what could and could not be reconstructed.
5. Create the state now so this does not happen twice.

## Handing over to a different agent or person

Use `memory/templates/HANDOFF.md`. It must stand alone: objective, current status with evidence, how to run and test, what is next, known problems, decisions already made and why, and what was tried and abandoned.
