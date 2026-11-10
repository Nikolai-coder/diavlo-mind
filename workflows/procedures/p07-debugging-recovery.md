# P07 — Error identification and recovery

## Trigger
- A command, test, build or tool fails, or
- behaviour differs from what was expected, or
- the same fix has been tried twice without success.

## Inputs
- The exact failure: full error text, exit code, the command and inputs that produced it.
- What changed most recently.
- The expected behaviour, stated concretely.

## Protocol
1. **Capture the failure verbatim.** Copy the whole message, including the first error rather than the last. Do not paraphrase before you understand it.
2. **Reproduce it** with one command you can re-run. If it does not reproduce, that is the first fact to investigate (state, timing, environment).
3. **Shrink it.** Remove inputs, steps and code until the failure almost disappears. The smallest failing case usually points at the cause.
4. **Check the cheap assumptions first:** right directory, right file, right version, saved changes, clean build, correct environment variables, the code you are editing is the code that runs.
5. **List hypotheses** — at most three — each with the observation that would confirm or kill it. Order them by likelihood times cheapness of the test.
6. **Test one hypothesis at a time.** Change one variable, predict the result, run, compare. Add logging or assertions at the boundary where good data becomes bad.
7. **Bisect when stuck:** between a working and a failing version, input or configuration, halve the difference until the cause is isolated.
8. **Explain the root cause** in one sentence that accounts for every symptom. If a symptom is unexplained, you have not found it yet.
9. **Fix the cause, not the symptom.** Then add a check that fails without the fix.
10. **Sweep for siblings.** Search for the same pattern elsewhere and for anything that depended on the broken behaviour.
11. **Confirm from clean.** Re-run the original reproduction and the wider suite from a clean state.

## Tools
- The failing command itself, re-run with more verbosity.
- Search for the error text and for the symbols in the stack trace.
- Logging, assertions, a debugger or a REPL at the suspected boundary.
- Version control: `git diff`, `git stash`, `git bisect` to compare with a working state.

## Outputs
```
Symptom: <exact error and command>
Root cause: <one sentence explaining all symptoms>
Evidence: <observation that confirms it>
Fix: <what changed, where>
Regression check: <test or command> → fails before, passes after
Related: <other places checked or fixed>
```

## Verification
- The original reproduction now passes, and you ran it.
- The regression check fails when the fix is reverted (or you can state precisely why it would).
- The wider suite shows no new failures compared with the baseline.
- The root-cause sentence leaves no symptom unexplained.

## Recovery
- **Two fixes failed:** stop editing. Re-read the full error literally, revert both attempts, and return to step 3. Your model of the problem is wrong, not your typing.
- **Cannot reproduce:** record the conditions under which it was seen, add instrumentation that will capture the next occurrence, and report it as unresolved.
- **The cause is outside your reach** (third-party bug, missing permission, infrastructure): confirm with the smallest example, document it, and propose a workaround clearly labelled as one.
- **Three distinct approaches failed:** escalate. Report what was tried, the evidence gathered, and the single most informative next experiment.
- **You are tempted to silence the error** (catch-all handler, skipped test, loosened assertion): that hides the failure; it does not recover from it. Do it only with the user's agreement and say so in the report.
