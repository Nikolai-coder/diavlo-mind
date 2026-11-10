# Benchmark

This folder answers one question with numbers instead of adjectives: **does a model do measurably better work with DIAVLO MIND than without it, and what does that cost?**

Results of the runs done for this release are in `evaluation/results/RESULTS.md`. This page describes the method, so that you can repeat it on your own model and check ours.

## Configurations

| | Configuration | What the model receives |
|---|---|---|
| **A** | Model without DIAVLO MIND | The task prompt only (`--arms baseline`) |
| **B** | Same model with DIAVLO MIND | The task prompt plus the framework instructions (`--arms diavlo-mind`) |
| **C** | Reference model | A stronger model, without the framework, on the same tasks. Optional: it shows how much room the tasks leave above A |

A and B use the same model, the same tools, the same task files and the same time limit. The only difference is the framework text. C is run with the same command as A and another `--model`.

## Tasks

Eight tasks, one per category of the brief. Each has a seeded workspace, a list of numbered requirements, hidden checks and a reference solution.

| Task | Category | What the agent must do | Requirements | Checks |
|---|---|---|---|---|
| `programming-duration` | programming | Write a duration parser and formatter with tests, from thirteen stated requirements | 13 | 19 |
| `debugging-inventory` | debugging | Fix five reported defects in a small package (one has a failing test) without rewriting it, and add regression tests | 9 | 15 |
| `architecture-notifications` | architecture | Design a notification service under three hard constraints, as a structured file plus a design document | 9 | 15 |
| `research-kestrel` | research | Answer nine questions from a local corpus that contains outdated, conflicting and missing information | 10 | 29 |
| `creative-short-script` | creative | Write a thirty-second vertical video script and its subtitle file under twelve production constraints | 12 | 12 |
| `longterm-notes-cli` | long-term project | Build a four-milestone command-line tool across two sessions that share files but no memory | 8 | 10 |
| `multiagent-briefs` | multi-agent | A lead writes two briefs; two isolated workers each build one module from its brief; the modules must work together | 6 | 8 |
| `recovery-migration` | error recovery | Complete a data migration where the documented command fails and the provided tool is wrong | 10 | 13 |

The corpus of `research-kestrel` describes an invented product, so the answers cannot come from a model's training data. `creative-short-script` and `architecture-notifications` have no single correct output; their checks verify the stated constraints only (see "What the checks cannot see").

## How a run works

1. The harness copies the task's seed files into a new workspace **in the system temp directory, outside this repository**. The hidden checks and the reference solution are never next to the agent.
2. The agent receives the task prompt, works in the workspace with its tools, and must end its last message with `STATUS: COMPLETE` or `STATUS: INCOMPLETE`.
3. Multi-stage tasks run each stage as a separate agent process. In `longterm-notes-cli` the second session sees only the files the first one left. In `multiagent-briefs` each worker sees only its own brief.
4. The harness runs the task's `checks/check.py` against a scratch copy of the final workspace and writes one `result.json` per run. Checks never touch the saved work, so scoring the same work again gives the same answer.

## Metrics

| Metric | Definition |
|---|---|
| Task success | Every required check passed. Reported as a rate over runs |
| Requirement coverage | Share of the task's numbered requirements whose checks all passed |
| Unresolved errors | Number of failed checks at the end of the run |
| Overclaim | The agent ended with `STATUS: COMPLETE` and the task was not solved. This is the "says done when it is not" failure the framework targets. In multi-stage tasks the claim is the one of the last stage; in `multiagent-briefs` that stage is a worker that cannot see the other worker's module, so read overclaims on that task with care |
| Underclaim | The agent ended with `STATUS: INCOMPLETE` and the task was solved |
| Code quality | For Python files the run created or changed: syntax errors, function length, nesting depth, bare `except`, unfinished-work markers. A cheap proxy, descriptive only, not part of success |
| Input / output tokens | As reported by the runner. For Claude Code, input includes cache reads and cache writes of every turn |
| Cost | As reported by the runner (`total_cost_usd` for Claude Code). It is the tool's own estimate, not an invoice |
| Turns, tool calls, duration | As reported by the runner; duration is wall-clock time of the agent process |

A metric that a runner does not report is stored as `null` and shown as "n/a". Nothing is estimated.

## Running it

```bash
# 0. The checks themselves: reject empty work, accept the reference solutions. No model is called.
python evaluation/selftest.py

# 1. A and B on one model, three trials per task
python evaluation/run_benchmark.py --runner claude-code --model <model> \
    --arms baseline diavlo-mind --trials 3 --keep-workspaces --label my-run

# 2. Aggregate and compare
python evaluation/score.py evaluation/runs/my-run
python evaluation/compare_runs.py evaluation/runs/my-run --arm-a baseline --arm-b diavlo-mind

# 2b. Or write a compact record you can publish: runs.jsonl, SUMMARY.md, COMPARISON.md
python evaluation/export_results.py evaluation/runs/my-run --out evaluation/results/my-model

# 3. Optional reference (configuration C)
python evaluation/run_benchmark.py --runner claude-code --model <stronger-model> --arms baseline --label my-reference
```

### Runners

| Runner | Use it for | How the framework is applied in arm B |
|---|---|---|
| `claude-code` | Claude Code installed locally (`claude -p`) | A prompt tier from `prompts/system/` is appended to the system prompt. Tools: Bash, Read, Edit, Write, Glob, Grep. Both arms run with `--safe-mode`, so no personal skills, plugins or memory files are loaded |
| `command` | Any agent CLI | You give a command template with `{prompt_file}`, `{workspace}`, `{system_file}`, `{model}`; arm B passes the prompt tier as `{system_file}` |
| `orchestrate` | Chat-only models through an API | Arm A is one raw completion. Arm B runs `scripts/dm_orchestrate.py` (plan, execute, repair, review) |
| `null`, `reference` | Testing the benchmark itself | Do nothing / copy the reference solution |

### Useful options

| Option | Meaning |
|---|---|
| `--tasks <ids or categories>` | Subset of tasks |
| `--trials N`, `--first-trial K` | Trials per task and arm; `--first-trial` adds trials to an earlier run |
| `--prompt-tier micro\|compact\|standard` | Which prompt tier arm B uses (default: standard) |
| `--max-budget-usd X` | Spending cap per stage for the `claude-code` runner (default 1.5) |
| `--timeout S` | Seconds per stage (default: the task's own limit) |
| `--keep-workspaces` | Keep the final workspaces in the results folder, so failures can be inspected and re-scored |
| `--rescore RUN_DIR` | Run the current checks again on kept workspaces. The original outcome stays in the result as `success_as_run` and `checks_as_run` |
| `--only CHECK_ID ...` | With `--rescore`: replace the outcome of the named checks and keep every other check as it was. Use it after correcting specific checks |

Results are written to `evaluation/runs/`, which git ignores. `export_results.py` copies what is worth publishing into `evaluation/results/`.

## Reading the comparison

`compare_runs.py` pairs runs by task and trial and reports success rate, overclaims, tokens and cost for both sides, then two exact two-sided sign tests on the pairs that differ: one on requirement coverage, one on task success. With fewer than six differing pairs it prints that no conclusion is possible, and above that it says in words whether the difference could be chance. Those sentences are part of the result; keep them when you quote the numbers.

## What the checks cannot see

- **Depth of reasoning.** A check verifies outputs. Two designs that both satisfy the constraints score the same, even if one is wiser.
- **Creative merit.** The creative task measures whether twelve production constraints hold, not whether the script is good. `rubrics/creative.md` and `rubrics/architecture.md` are scoring guides for a human or a separate judge model; the harness does not apply them.
- **The skill's on-demand loading and its role agents.** Arm B of the `claude-code` runner receives one prompt tier as a system prompt. The twenty procedures loaded on demand, the mode files and the eight subagents are not exercised by it. To measure those, install the skill and run the tasks through the `command` runner with an agent command that loads it.
- **Long horizons.** The longest task is two sessions and four milestones. It tests whether written state survives a session boundary, not multi-day projects.
- **Your tasks.** Eight tasks are a small sample. A result here predicts little about work that looks different.

## Threats to validity, and what was done about each

| Threat | Mitigation |
|---|---|
| Checks that pass anything | `selftest.py` requires that an empty submission fails every task and passes at most half of its checks |
| Checks that reject correct work | `selftest.py` requires that the reference solution passes every check. Four checks found stricter than their task text during the pilot were corrected, and both outcomes are published (see the results file) |
| The agent reads the checks | Workspaces live outside the repository; `--safe-mode` keeps the repository's own instructions out |
| Small samples | Every table states the number of runs; the sign test refuses to conclude below six differing pairs |
| The framework's author also wrote the tasks | Not mitigated. Results from other people's tasks are welcome: use the "Benchmark result" issue template |
| Model non-determinism | Several trials per task; per-run results are published, not only averages |

## Adding a task

```
evaluation/tasks/<id>/
    task.json        id, title, category, requirements, stages, timeout_seconds
    prompt.md        what the agent is told
    workspace/       seed files (optional)
    checks/check.py  hidden checks, built on evaluation/lib/checklib.py
    reference/       a solution that passes every check
```

Then run `python evaluation/selftest.py --tasks <id>` until the empty submission is rejected, the reference is accepted and every requirement has a check. `scripts/validate.py` verifies the layout.

## Files

| Path | Purpose |
|---|---|
| `run_benchmark.py` | The harness: workspaces, runners, stages, checks, `result.json` |
| `score.py` | Aggregates results into `summary.json` and `SUMMARY.md` |
| `compare_runs.py` | Paired comparison of two arms or two framework versions |
| `export_results.py` | Compact, publishable record of a runs folder |
| `selftest.py` | Tests the checks with an empty and a reference submission |
| `lib/checklib.py`, `lib/quality.py` | Helpers for checks and the descriptive code metrics |
| `tasks/` | The eight tasks |
| `rubrics/` | Human scoring guides for the two tasks without a single right answer |
| `results/` | Published results of this release |
| `improvement/` | The improvement log and the fingerprint of the ten core rules |
