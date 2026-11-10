# Benchmark summary

Generated 2026-11-10T13:36:11Z from 48 run(s).

| Run folder | Runner | Model requested | Arm(s) | Trials | Tasks | Prompt tier | Framework | Agent version | Started (UTC) |
|---|---|---|---|---|---|---|---|---|---|
| `pilot-haiku45/baseline-a` | claude-code | `claude-haiku-4-5` | baseline | 1-3 | 4 | — | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T13:05:02Z |
| `pilot-haiku45/baseline-b` | claude-code | `claude-haiku-4-5` | baseline | 1-3 | 4 | — | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T13:05:02Z |
| `pilot-haiku45/dm-a` | claude-code | `claude-haiku-4-5` | diavlo-mind | 1-3 | 4 | standard | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T13:05:02Z |
| `pilot-haiku45/dm-b` | claude-code | `claude-haiku-4-5` | diavlo-mind | 1-3 | 4 | standard | 1.0.0 | 2.1.322 (Claude Code) | 2026-11-10T13:05:02Z |

## How to read this

- Each cell is measured from executed runs. Trials per task and arm: 3.
- With 3 trials per task, a difference of one or two runs between configurations is still within run-to-run variation. Use `compare_runs.py` for the paired comparison and its sign test before drawing conclusions.
- Success means every hidden check of a task passed. Requirement coverage is the share of a task's requirements whose checks all passed.
- An overclaim is a run whose final message said `STATUS: COMPLETE` while a check failed.
- "As first scored" is the outcome before any check was corrected and the saved workspaces were re-scored. When the two success rates are equal, no correction changed an outcome.
- Cost is the figure the runner reported, not a bill.

## By configuration

| Metric | claude-haiku-4-5 · baseline | claude-haiku-4-5 · diavlo-mind |
|---|---|---|
| Runs | 24 | 24 |
| Task success rate | 58% | 75% |
| Task success rate as first scored | 58% | 75% |
| Runs whose checks changed on re-scoring | 1 | 2 |
| Checks passed | 96% | 97% |
| Functional correctness (mean) | 96% | 100% |
| Requirement coverage (mean) | 93% | 94% |
| Unresolved errors per run | 0.62 | 0.46 |
| Runs claiming COMPLETE | 24 | 24 |
| Overclaims (claimed COMPLETE, checks failed) | 10 | 6 |
| Runs without a STATUS line | 0 | 0 |
| Code-quality proxy (0-1) | 0.94 | 0.93 |
| Input tokens per run | 956,255 | 926,920 |
| Output tokens per run | 14,533 | 13,458 |
| Cost per run (USD, as reported by the runner) | 0.228 | 0.218 |
| Cost total (USD) | 5.47 | 5.23 |
| Turns per run | 21.8 | 20.2 |
| Tool calls per run | 20.5 | 18.9 |
| Seconds per run | 112 | 104 |
| Tasks solved in every trial | 4 | 5 |
| Tasks solved in at least one trial | 6 | 7 |

## By task

| Task | Category | claude-haiku-4-5 · baseline: solved · checks · coverage · out tokens · cost | claude-haiku-4-5 · diavlo-mind: solved · checks · coverage · out tokens · cost |
|---|---|---|---|
| architecture-notifications | architecture | 0/3 · 41/45 · 85% · 24,747 · 0.312 | 1/3 · 40/45 · 82% · 15,468 · 0.184 |
| creative-short-script | creative | 3/3 · 36/36 · 100% · 11,742 · 0.127 | 3/3 · 36/36 · 100% · 10,148 · 0.119 |
| debugging-inventory | debugging | 1/3 · 42/45 · 89% · 7,219 · 0.186 | 3/3 · 45/45 · 100% · 6,946 · 0.172 |
| longterm-notes-cli | long-term-project | 0/3 · 25/30 · 79% · 27,406 · 0.546 | 0/3 · 25/30 · 79% · 27,887 · 0.587 |
| multiagent-briefs | multi-agent | 3/3 · 24/24 · 100% · 14,620 · 0.213 | 2/3 · 23/24 · 94% · 13,342 · 0.203 |
| programming-duration | programming | 3/3 · 57/57 · 100% · 13,877 · 0.154 | 3/3 · 57/57 · 100% · 16,639 · 0.170 |
| recovery-migration | error-recovery | 1/3 · 36/39 · 90% · 12,822 · 0.219 | 3/3 · 39/39 · 100% · 13,061 · 0.226 |
| research-kestrel | research | 3/3 · 87/87 · 100% · 3,830 · 0.066 | 3/3 · 87/87 · 100% · 4,177 · 0.082 |

## Failed checks

- **architecture-notifications** — claude-haiku-4-5 · baseline: decisions-complete, interfaces-complete
- **architecture-notifications** — claude-haiku-4-5 · diavlo-mind: decisions-complete, design-length, design-names-components, interfaces-complete
- **debugging-inventory** — claude-haiku-4-5 · baseline: discount-half-up, regression-test-bug3
- **longterm-notes-cli** — claude-haiku-4-5 · baseline: m4-export, session-1-leaves-handoff, tests-cover-milestones
- **longterm-notes-cli** — claude-haiku-4-5 · diavlo-mind: session-1-leaves-handoff, tests-cover-milestones
- **multiagent-briefs** — claude-haiku-4-5 · diavlo-mind: deliveries-in-scope
- **recovery-migration** — claude-haiku-4-5 · baseline: rejected-raw-and-order, rejected-reasons, summary-correct
