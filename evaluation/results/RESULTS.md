# Results — DIAVLO MIND 1.0.0, pilot benchmark

Run on 2026-11-10. Method: `evaluation/README.md`. Raw per-run records: `evaluation/results/haiku-4-5/runs.jsonl` and `evaluation/results/haiku-5-5/runs.jsonl`.

## Short version

- **Older small model (`claude-haiku-4-5`):** with the framework it solved **18 of 24** runs, without it **14 of 24**, at about the same cost (0.96 times). The gain came from the debugging and error-recovery tasks. **The difference is not statistically established**: in the paired comparison the framework arm solved 5 runs that the baseline did not and lost 1 that the baseline solved (exact sign test, p = 0.22).
- **Newer small model (`claude-haiku-5-5`):** both configurations were at the ceiling of this suite, **23 of 24** without and **24 of 24** with the framework (23 of 24 as first scored). The benchmark cannot show an effect on this model. The framework made the runs **28% more expensive** (25% more output tokens).
- **Completion claims:** all 96 runs ended with `STATUS: COMPLETE`. No run in either configuration ever reported `INCOMPLETE`, so every failed run was an overclaim. The framework reduced the number of failed runs on the older model (10 to 6); it did not make a failing run say so.
- **Where the framework did not work:** on the two-session task the older model left no written handoff in 3 of 3 runs with the framework (2 of 3 without), although writing state down is one of the ten rules.
- **Not measured:** the stronger reference model (configuration C), any non-Claude model, and the skill's on-demand procedures and subagents.

These are 96 runs of eight tasks written by the framework's author. They describe this suite on these two models. They are not evidence about other models or other kinds of work.

## What was run

| | |
|---|---|
| Tasks | 8, one per category (`evaluation/tasks/`) |
| Configurations | A: task prompt only. B: task prompt plus the standard prompt tier (14,154 characters) appended to the agent's system prompt |
| Models | `claude-haiku-4-5` and `claude-haiku-5-5` (requested as `haiku`; the id is the one the CLI reported) |
| Trials | 3 per task and configuration: 24 runs per configuration and model, 96 in total |
| Runner | `claude-code`: Claude Code 2.1.322, `claude -p`, tools Bash, Read, Edit, Write, Glob, Grep, `--safe-mode`, spending cap 1.50 USD per stage |
| Environment | Linux container, Python 3.13 |
| Cost reported by the CLI | 10.70 USD for `claude-haiku-4-5`, 0.73 USD for `claude-haiku-5-5`, 11.43 USD in total |
| Runs that errored or timed out | 0 |

## claude-haiku-4-5

| Metric | A: without | B: with DIAVLO MIND |
|---|---|---|
| Runs | 24 | 24 |
| Tasks solved (all hidden checks pass) | 14/24 (58%) | 18/24 (75%) |
| Same, as first scored | 14/24 (58%) | 18/24 (75%) |
| Runs that ended with `STATUS: COMPLETE` | 24 | 24 |
| Overclaims (said COMPLETE, a check failed) | 10 | 6 |
| Requirement coverage, mean | 93% | 94% |
| Failed checks per run, mean | 0.62 | 0.46 |
| Output tokens per run | 14,533 | 13,458 |
| Input tokens per run (with cache reads) | 956,255 | 926,920 |
| Cost per run, USD (as the CLI reports it) | 0.228 | 0.218 |
| Turns per run | 21.8 | 20.2 |
| Seconds per run | 112 | 104 |

| Task | A solved | B solved | A failed checks | B failed checks |
|---|---|---|---|---|
| `architecture-notifications` | 0/3 | 1/3 | `decisions-complete`, `interfaces-complete` | `decisions-complete`, `design-length`, `design-names-components`, `interfaces-complete` |
| `creative-short-script` | 3/3 | 3/3 | — | — |
| `debugging-inventory` | 1/3 | 3/3 | `discount-half-up`, `regression-test-bug3` | — |
| `longterm-notes-cli` | 0/3 | 0/3 | `m4-export`, `session-1-leaves-handoff`, `tests-cover-milestones` | `session-1-leaves-handoff`, `tests-cover-milestones` |
| `multiagent-briefs` | 3/3 | 2/3 | — | `deliveries-in-scope` |
| `programming-duration` | 3/3 | 3/3 | — | — |
| `recovery-migration` | 1/3 | 3/3 | `rejected-raw-and-order`, `rejected-reasons`, `summary-correct` | — |
| `research-kestrel` | 3/3 | 3/3 | — | — |

Paired by task and trial (24 pairs), from `haiku-4-5/COMPARISON.md`:

- Task success: B solved and A did not in 5 pairs; A solved and B did not in 1. Exact two-sided sign test on the 6 differing pairs: **p = 0.219**.
- Requirement coverage: B higher in 6 pairs, lower in 3, equal in 15. Sign test: **p = 0.508**.

Neither test separates the two configurations from chance. Read "18 against 14" as a direction worth a larger run, not as a result.

## claude-haiku-5-5

| Metric | A: without | B: with DIAVLO MIND |
|---|---|---|
| Runs | 24 | 24 |
| Tasks solved (all hidden checks pass) | 23/24 (96%) | 24/24 (100%) |
| Same, as first scored | 23/24 (96%) | 23/24 (96%) |
| Runs that ended with `STATUS: COMPLETE` | 24 | 24 |
| Overclaims (said COMPLETE, a check failed) | 1 | 0 |
| Requirement coverage, mean | 99% | 100% |
| Failed checks per run, mean | 0.04 | 0.00 |
| Output tokens per run | 11,473 | 14,386 |
| Input tokens per run (with cache reads) | 299,828 | 410,403 |
| Cost per run, USD (as the CLI reports it) | 0.013 | 0.017 |
| Turns per run | 9.2 | 9.9 |
| Seconds per run | 52 | 64 |

| Task | A solved | B solved | A failed checks | B failed checks |
|---|---|---|---|---|
| `architecture-notifications` | 3/3 | 3/3 | — | — |
| `creative-short-script` | 3/3 | 3/3 | — | — |
| `debugging-inventory` | 3/3 | 3/3 | — | — |
| `longterm-notes-cli` | 2/3 | 3/3 | `session-1-leaves-handoff` | — |
| `multiagent-briefs` | 3/3 | 3/3 | — | — |
| `programming-duration` | 3/3 | 3/3 | — | — |
| `recovery-migration` | 3/3 | 3/3 | — | — |
| `research-kestrel` | 3/3 | 3/3 | — | — |

One pair differs, so no test is possible. The single extra success of B appears only after a check was corrected (see "Corrections made to checks during the pilot"); as first scored the two configurations were equal at 23 of 24.

## What the framework arm got wrong

Recorded as open failures F1 to F4 in `evaluation/improvement/failures.jsonl` (list them with `python scripts/dm_improve.py list`). None is classified yet: telling inadequate instructions from a limit of the model needs the rerun described in `workflows/protocols/self-improvement.md`.

1. **F1 — No handoff across sessions (`longterm-notes-cli`, `claude-haiku-4-5`).** The first session was told that another engineer would continue from the files alone. With the framework, 3 of 3 first sessions ended without any file saying what was left; in all three the handoff existed only in the final chat message, which the next session never sees. In 2 of those 3 runs the second session then added the remaining features without tests. Rule 9 ("write state down") was in the prompt and was not followed.
2. **F2 — Extra files in a delivery (`multiagent-briefs`, `claude-haiku-4-5`, 1 of 3 runs).** A worker told to deliver exactly one module also left two test files next to it. Without the framework this did not happen in 3 runs. The framework asks for tests; here that collided with an explicit scope instruction, and scope lost.
3. **F4 — Format rules of a specification (`architecture-notifications`, `claude-haiku-4-5`).** 2 of 3 framework runs broke rules stated in the task's format file: a chosen option that was not literally one of the listed options, a document over the stated length, an interface provided by a component that does not exist. The baseline broke such rules in 3 of 3 runs.
4. **F3 — No honest `INCOMPLETE`.** See the short version. Rule 6 ("prove, don't claim") did not change what a failing run reported.

## Corrections made to checks during the pilot

A hidden check may only fail what the task text states. Four checks were stricter than their task text. Each was corrected, every saved workspace was re-scored for those checks only, and the outcome as first scored is kept in the run records (`success_as_first_scored`, `failed_checks_as_first_scored`).

| Check | Task | What was wrong | Correction | Runs whose checks changed | Outcomes changed |
|---|---|---|---|---|---|
| `modules-not-rewritten` | `debugging-inventory` | Required 0.60 text similarity to the original module; the reference fix itself reached only 0.64 on a twelve-line file | At least half of each module's original lines must survive | 1 (`claude-haiku-5-5`, B, trial 1) | **1: failed to solved** |
| `m4-export` | `longterm-notes-cli` | Required the exported file to end with a newline; the specification does not say | The final newline is optional | 2 (`claude-haiku-4-5`, B, trials 1 and 2) | 0 |
| `design-sections` | `architecture-notifications` | Compared headings with exact letter case ("Data Flow" failed) | Letter case is ignored | 1 (`claude-haiku-4-5`, A, trial 2) | 0 |
| `design-names-components` | `architecture-notifications` | Required component ids to appear in kebab case in the document ("Rate Limiter" failed for `rate-limiter`) | The words of the id must appear, in any case and with any separator | 1 (same run) | 0 |

The one changed outcome favours the framework arm, which is why both figures are shown everywhere: 24 of 24 after the correction, 23 of 24 before it.

Two requirements of `longterm-notes-cli` are implied by the prompt rather than spelled out, and were **not** relaxed: that the first session leaves a written note naming what remains (the prompt says "leave the project in a state they can continue from"), and that the second session's features have tests (the specification says where tests live). They account for 9 of the 11 failed checks on that task across both models. A stricter reader could call them unfair; state them explicitly if you reuse the task.

One defect was found in the harness itself. Checks ran inside the agent's workspace, so a check that runs the agent's own test suite could alter the saved copy, and scoring the same work twice could differ. Checks now run on scratch copies, and scoring is repeatable (`tests/test_benchmark_pipeline.py`).

## Not run

| What | Why | How to run it |
|---|---|---|
| Configuration C, a stronger reference model | `claude-haiku-5-5` already solves 23 of 24 runs without the framework, so a stronger reference could only confirm the ceiling. A single completion on the strongest available model cost about 0.41 USD in `examples/02-fable-advisor-orchestrator/`; eight agentic tasks would cost a multiple of the whole pilot | `python evaluation/run_benchmark.py --runner claude-code --model <reference-model> --arms baseline --max-budget-usd 6` |
| OpenAI, Gemini and local models | No credentials or servers in the build environment | `--runner orchestrate --executor <provider>:<model>` or `--runner command` |
| The skill with on-demand procedures and subagents | The harness applies the framework as one prompt tier, to keep both configurations on the same tools | `--runner command` with an agent command that loads the installed skill |
| More than 3 trials | Cost | `--trials N --first-trial 4` adds trials to the existing runs |
| The compact and micro prompt tiers | Cost | `--prompt-tier compact` |

## Reproduce

```bash
python evaluation/selftest.py
python evaluation/run_benchmark.py --runner claude-code --model claude-haiku-4-5 \
    --arms baseline diavlo-mind --trials 3 --keep-workspaces --label repro-haiku-4-5
python evaluation/export_results.py evaluation/runs/repro-haiku-4-5 --out evaluation/results/repro-haiku-4-5
```

Models are not deterministic: expect the per-task counts to move by a run or two.

## Files in this folder

| Path | Content |
|---|---|
| `haiku-4-5/runs.jsonl`, `haiku-5-5/runs.jsonl` | One line per run: outcome, failed checks with their detail, claim, tokens, cost, turns, duration, and the outcome as first scored where a check was corrected |
| `haiku-4-5/SUMMARY.md`, `haiku-5-5/SUMMARY.md` | Aggregates by configuration and by task, written by `score.py` |
| `haiku-4-5/COMPARISON.md`, `haiku-5-5/COMPARISON.md` | The paired comparison, pair by pair, written by `compare_runs.py` |
| `haiku-4-5/summary.json`, `haiku-5-5/summary.json` | The aggregates as data |
