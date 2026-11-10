# P16 — Iterative improvement

## Trigger
- A first version works but misses a quality target (speed, clarity, accuracy, size, polish), or
- the user asked to "improve", "optimize" or "polish" something that already exists.

## Inputs
- The working version and the checks that prove it works.
- The target: a number or a concrete description of "good enough".
- The budget: how many iterations, how much time or cost.

## Protocol
1. **Freeze correctness first.** Make sure the checks that prove the current version works exist and pass. They are the guard for every later change.
2. **Define the measure.** Turn "better" into something you can observe: runtime of a named command, word count, error rate on a fixed sample, a rubric score, a reviewer's list of defects.
3. **Measure the baseline** and write it down with the exact method.
4. **Find the biggest gap.** Profile, read the reviewer's findings, or rank the rubric items. Work on the largest contributor, not the most interesting one.
5. **Make one change.** One idea per iteration so the effect can be attributed.
6. **Re-measure with the same method,** then re-run the correctness checks.
7. **Keep or revert.** Keep the change only if the measure improved and nothing broke. Otherwise revert fully — no half-kept experiments.
8. **Log each iteration:** change, measure before and after, decision.
9. **Stop** when the target is met, when two consecutive iterations bring no meaningful gain, or when the budget is spent. Polishing past the target is waste.

## Tools
- A timer, profiler, counter or scoring script — whatever produces the measure reproducibly.
- The correctness test suite.
- Version control to revert cleanly.
- `agents/dm-optimizer.md` for a dedicated pass; `agents/dm-reviewer.md` for a defect list.

## Outputs
```
| # | Change | Measure before | After | Kept |
| 0 | baseline | 4.8 s | — | — |
| 1 | cache parsed config | 4.8 s | 2.1 s | yes |
| 2 | parallel file reads | 2.1 s | 2.0 s | no (within noise) |
Result: 4.8 s → 2.1 s on `make bench` (mean of 5 runs); 42 tests still pass.
```

## Verification
- Baseline and final numbers come from the same method, stated in the report.
- Correctness checks passed after the final kept change.
- Every kept change has a measured gain; no change is kept on belief alone.
- The stopping reason is stated.

## Recovery
- **The measure is noisy:** repeat runs and compare means or medians; treat differences inside the spread as no gain.
- **An improvement broke correctness:** revert it. Speed or polish never outranks a failing check.
- **No change helps:** the bottleneck is elsewhere. Re-measure where the time, errors or weakness really are before trying again.
- **The target is unreachable in this design:** report the best achieved result, the limiting factor, and the design change that would be needed.
