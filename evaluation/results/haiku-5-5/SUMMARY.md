# Benchmark summary

Generated 2026-11-10T13:36:11Z from 48 run(s).

| Run folder | Runner | Model requested | Arm(s) | Trials | Tasks | Prompt tier | Framework | Agent version | Started (UTC) |
|---|---|---|---|---|---|---|---|---|---|
| `pilot-haiku/baseline-a` | claude-code | `haiku` | baseline | 1 | 4 | — | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T12:57:01Z |
| `pilot-haiku/baseline-a-t23` | claude-code | `haiku` | baseline | 2-3 | 4 | — | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T13:05:02Z |
| `pilot-haiku/baseline-b` | claude-code | `haiku` | baseline | 1 | 4 | — | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T12:57:01Z |
| `pilot-haiku/baseline-b-t23` | claude-code | `haiku` | baseline | 2-3 | 4 | — | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T13:05:02Z |
| `pilot-haiku/dm-a` | claude-code | `haiku` | diavlo-mind | 1 | 4 | standard | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T12:57:01Z |
| `pilot-haiku/dm-a-t23` | claude-code | `haiku` | diavlo-mind | 2-3 | 4 | standard | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T13:05:02Z |
| `pilot-haiku/dm-b` | claude-code | `haiku` | diavlo-mind | 1 | 4 | standard | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T12:57:01Z |
| `pilot-haiku/dm-b-t23` | claude-code | `haiku` | diavlo-mind | 2-3 | 4 | standard | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T13:05:02Z |

## How to read this

- Each cell is measured from executed runs. Trials per task and arm: 3.
- With 3 trials per task, a difference of one or two runs between configurations is still within run-to-run variation. Use `compare_runs.py` for the paired comparison and its sign test before drawing conclusions.
- Success means every hidden check of a task passed. Requirement coverage is the share of a task's requirements whose checks all passed.
- An overclaim is a run whose final message said `STATUS: COMPLETE` while a check failed.
- "As first scored" is the outcome before any check was corrected and the saved workspaces were re-scored. When the two success rates are equal, no correction changed an outcome.
- Cost is the figure the runner reported, not a bill.

## By configuration

| Metric | claude-haiku-5-5 · baseline | claude-haiku-5-5 · diavlo-mind |
|---|---|---|
| Runs | 24 | 24 |
| Task success rate | 96% | 100% |
| Task success rate as first scored | 96% | 96% |
| Runs whose checks changed on re-scoring | 0 | 1 |
| Checks passed | 100% | 100% |
| Functional correctness (mean) | 100% | 100% |
| Requirement coverage (mean) | 99% | 100% |
| Unresolved errors per run | 0.04 | 0.00 |
| Runs claiming COMPLETE | 24 | 24 |
| Overclaims (claimed COMPLETE, checks failed) | 1 | 0 |
| Runs without a STATUS line | 0 | 0 |
| Code-quality proxy (0-1) | 0.99 | 0.99 |
| Input tokens per run | 299,828 | 410,403 |
| Output tokens per run | 11,473 | 14,386 |
| Cost per run (USD, as reported by the runner) | 0.013 | 0.017 |
| Cost total (USD) | 0.32 | 0.41 |
| Turns per run | 9.2 | 9.9 |
| Tool calls per run | 7.8 | 8.5 |
| Seconds per run | 52 | 64 |
| Tasks solved in every trial | 7 | 8 |
| Tasks solved in at least one trial | 8 | 8 |

## By task

| Task | Category | claude-haiku-5-5 · baseline: solved · checks · coverage · out tokens · cost | claude-haiku-5-5 · diavlo-mind: solved · checks · coverage · out tokens · cost |
|---|---|---|---|
| architecture-notifications | architecture | 3/3 · 45/45 · 100% · 22,954 · 0.020 | 3/3 · 45/45 · 100% · 24,437 · 0.024 |
| creative-short-script | creative | 3/3 · 36/36 · 100% · 5,674 · 0.007 | 3/3 · 36/36 · 100% · 7,734 · 0.011 |
| debugging-inventory | debugging | 3/3 · 45/45 · 100% · 6,028 · 0.009 | 3/3 (first scored 2/3) · 45/45 · 100% · 8,071 · 0.012 |
| longterm-notes-cli | long-term-project | 2/3 · 29/30 · 96% · 17,296 · 0.023 | 3/3 · 30/30 · 100% · 23,927 · 0.032 |
| multiagent-briefs | multi-agent | 3/3 · 24/24 · 100% · 18,039 · 0.022 | 3/3 · 24/24 · 100% · 23,815 · 0.028 |
| programming-duration | programming | 3/3 · 57/57 · 100% · 7,492 · 0.008 | 3/3 · 57/57 · 100% · 10,082 · 0.011 |
| recovery-migration | error-recovery | 3/3 · 39/39 · 100% · 10,953 · 0.012 | 3/3 · 39/39 · 100% · 13,446 · 0.014 |
| research-kestrel | research | 3/3 · 87/87 · 100% · 3,351 · 0.006 | 3/3 · 87/87 · 100% · 3,578 · 0.006 |

## Failed checks

- **longterm-notes-cli** — claude-haiku-5-5 · baseline: session-1-leaves-handoff
