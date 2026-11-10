# Example 01 — the skill in Claude Code

**What was run.** Claude Code 2.1.322 in headless mode on 2026-11-10, model alias `haiku` (reported as `claude-haiku-5-5`), with this repository loaded as a plugin and the skill invoked explicitly.

```bash
cp -r project-before /tmp/demo && cd /tmp/demo
(printf "/diavlo-mind:diavlo-mind "; cat ../task.md) | claude -p --model haiku \
  --plugin-dir /path/to/diavlo-mind \
  --permission-mode acceptEdits --allowedTools "Bash,Read,Edit,Write,Glob,Grep,Skill" \
  --output-format stream-json --verbose --no-session-persistence --max-budget-usd 1.0
```

**The request** (`task.md`): add a `--since YYYY-MM-DD` option to `export.py`, reject invalid dates with exit code 2, document it, keep the existing tests passing and add new ones.

## What happened

| | |
|---|---|
| Mode chosen by the model | STANDARD |
| Tool calls | 14 (list in `run.json`) |
| Turns | 15 |
| Output tokens | 7,789 |
| Cost reported by Claude Code | $0.0142 |
| Duration | 35.6 s |

The order of work, from `run.json`: list the project → read `export.py`, `README.md`, the tests and the data → **run the existing tests first (baseline: 4 passed)** → edit the code → add tests → run the suite → try an invalid date by hand → edit the README → run everything once more.

The complete final message is in `final-message.md`. It ends with the delivery block: one evidence row per requirement, each citing a command that ran, followed by two limitations the model found in its own work (a malformed date inside the CSV raises a traceback; `strptime` accepts `2024-1-5`), its assumptions and a next step.

## Independent check

These were run afterwards, outside the session, on `project-after/`:

```
$ python3 -m unittest discover -s tests
Ran 12 tests ... OK
$ python3 export.py orders.csv --since 2024-02-01
2024-02-01  initech       310.00
2024-02-14  acme           15.25
2024-03-02  hooli          99.99
$ python3 export.py orders.csv --since 2024-13-01; echo $?
export.py: error: argument --since: invalid date '2024-13-01', expected YYYY-MM-DD
2
$ grep -n since README.md        # two matches: the usage example and the option description
```

All four requirements of the request hold. The two limitations the model reported are real and were not asked for.

## FAST mode, same setup

A trivial question through the same command (`/diavlo-mind:diavlo-mind What is 12*12? Answer briefly.`) returned, in full:

> **144**
>
> Checked by splitting it: 10×12 = 120 and 2×12 = 24, and 120 + 24 = 144.

No plan, no table: the result and one line on how it was checked. Reported cost: $0.0014.

## What this example does not show

One run on one task with one model. It shows that the skill loads, is followed, and produces a verifiable report; it says nothing about how much the skill changes outcomes. For that see `evaluation/`.
