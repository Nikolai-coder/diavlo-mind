# P19 — Independent verification

## Trigger
- The work is in DEEP or AUTONOMOUS mode and is about to be delivered, or
- an error would be costly (security, money, data, public release), or
- the author's own checks are the only evidence so far.

## Inputs
- The requirement list and acceptance criteria.
- The artifact, exactly as it would be delivered.
- Instructions for running it. **Not** the author's reasoning, notes or self-assessment.

## Protocol
1. **Separate the verifier from the author.** Use a different agent or a fresh context. It receives the requirements and the artifact only. What the author believed is deliberately withheld; a reviewer who reads the author's argument tends to agree with it.
2. **Derive expectations first.** Before looking at results, the verifier writes what correct behaviour would be for each requirement and for a few edge cases.
3. **Execute, do not read about execution.** The verifier runs the checks itself, from a clean state, using the documented commands. Reported results from the author count for nothing here.
4. **Try to break it.** Boundaries, invalid input, missing files, repeated runs, the largest plausible input, the first thing a careless user would do.
5. **Read the change for what tests cannot see:** unhandled errors, security problems, unclear names, needless complexity, edits outside the task.
6. **Report findings, not opinions.** Each finding has a severity, a location, what was observed, how to reproduce it, and a suggested fix:
   - **blocker** — a requirement is not met, or data, security or correctness is at risk;
   - **major** — works, but will cause trouble soon;
   - **minor** — improvement worth making;
   - **note** — observation, no action required.
7. **Verdict:** PASS (no blockers, requirements verified), PASS WITH ISSUES (list them), or FAIL (which requirement, what evidence).
8. **The author fixes; the verifier re-checks** the fixed items and anything they could have affected. The loop ends when the verdict is PASS or the remaining issues are accepted in writing by the user.

## Tools
- A reviewer agent (`agents/dm-reviewer.md`) and a validator agent (`agents/dm-validator.md`) with fresh context.
- A different model as reviewer where available; diversity catches more.
- A clean checkout or directory for execution.
- `prompts/templates/review-request.md` and `prompts/templates/validation-report.md`.

## Outputs
```
Verdict: PASS WITH ISSUES
| # | Severity | Where | Finding | Reproduce | Suggested fix |
| 1 | major | export.py:88 | --since ignores timezone, off by one day near midnight UTC | run with TZ=Asia/Tokyo, --since 2024-03-01 | compare in UTC |
Requirements re-verified: R1 R2 R3 R5 (commands and results attached). R4 not verifiable: README not rendered here.
```

## Verification
- The verifier's context did not contain the author's reasoning.
- Every requirement was checked by execution or direct inspection by the verifier.
- Each finding can be reproduced from the report.
- Fixed findings were re-checked after the fix.

## Recovery
- **No second agent or context is available:** do a cold read. Close your notes, re-read only the requirements, write expectations, then inspect the artifact as if a stranger wrote it. Say in the report that the review was not independent.
- **Verifier and author disagree:** settle it with a test both accept. If no test can decide, present both positions to the user.
- **The verifier cannot run the artifact:** the verdict is NOT VERIFIED for those requirements, never PASS.
- **Findings keep appearing after fixes:** the design, not the patch, is the problem. Return to `p06-architecture-design` or `p07-debugging-recovery`.
