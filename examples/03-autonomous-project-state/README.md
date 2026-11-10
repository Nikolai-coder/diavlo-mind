# Example 03 — project state across a session break

`session.txt` is the unedited output of the commands shown in it, run with `scripts/dm_state.py` (the timestamp is fixed with `DM_NOW` so the output is reproducible). `state.json` and `STATE.md` are the files it left behind.

What to look at:

- **Requirements and tasks are linked.** Each task names the requirements it covers and the files it may write; `validate` confirms there are no cycles and no uncovered requirements.
- **Shortcuts are refused.** Starting T2 before T1 is finished fails. Marking T1 done without evidence fails, with the rule quoted.
- **The break.** After the checkpoint, `resume` prints everything a new session needs: objective, definition of done, progress, the next action, the open question, what is ready, and the instruction to verify the claims against the real files first.
- **Done is proven, not declared.** `done-check` exits 1 with a list of gaps until every requirement has evidence and every task is done or dropped; then it exits 0 and prints the definition-of-done checks to run.

Reproduce:

```bash
mkdir /tmp/demo3 && export DM_NOW=2026-11-10T12:00:00Z
python scripts/dm_state.py --dir /tmp/demo3 init --objective "Ship the --since filter for the export tool" --mode autonomous
# ... the remaining commands are in session.txt
```
