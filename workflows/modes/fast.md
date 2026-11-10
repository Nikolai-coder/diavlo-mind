# FAST mode

For straightforward tasks. Optimized for speed and low overhead.

## Entry conditions (all must hold)

- One clear step, or a well-known transformation.
- At most one file changed, or the output is a short answer.
- Nothing unknown: you already have, or can read in one call, everything needed.
- Trivially reversible: no deletion, publication, payment, migration or external side effect.

If any condition is false, use STANDARD.

## Workflow

1. **Frame silently.** Know the objective and the one or two requirements. Do not print a requirement list.
2. **Look once.** If the answer depends on a file, error or value, read it. One read-only call is normal; guessing is not.
3. **Do it.** Smallest change or shortest correct answer.
4. **Check once.** Run it, re-read the changed lines, or recompute the number. Pick whichever check could actually fail.
5. **Deliver.** The result, plus one line saying how it was checked. No headings, no table, no restated request.

## Budget

- About 1–5 tool calls. More than that means the task was not FAST.
- Output length: what the answer needs. A one-line answer stays one line.

## What FAST does not include

No written plan, no agents, no state files, no evidence table, no option analysis.

## Escalate to STANDARD when

- The single check fails and the fix is not obvious.
- The change needs a second file or a second step you did not expect.
- You notice an assumption you cannot confirm in one call.

When escalating, say so in one line and continue; do not restart the conversation.

## Example

Request: "Rename the `--verbose` flag to `--debug` in `cli.py`."

- Read `cli.py`, find the flag definition and its two uses.
- Edit the three places.
- Run `python cli.py --debug --help` → exits 0 and lists `--debug`.
- Reply: "Renamed in `cli.py` (definition and 2 uses). Checked: `python cli.py --debug --help` exits 0. Note: `README.md` still mentions `--verbose` — not changed, out of scope."
