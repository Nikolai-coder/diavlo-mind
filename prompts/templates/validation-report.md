# Validation report

```
Subject: <what was validated, version or commit>
Environment: <OS, runtime and tool versions>
Verdict: CONFIRMED | NOT CONFIRMED

| Req | Check (exact command or inspection) | Expected | Observed | Result |
|-----|-------------------------------------|----------|----------|--------|
| R1 | … | … | … | pass |
| R2 | … | … | … | fail |
| R3 | … | … | not executed: <why> | not verified |

Baseline: <test results before the change, if recorded>
Now: <test results after>
Regressions: <tests that passed before and fail now, or "none">

Failures in detail:
  R2 — expected <…>, observed <…>, minimal reproduction: `<command>`

Not verified: <each item, with the command for someone who can run it>
```

Rules: a row is `pass` only if the validator ran the check in this session · `not verified` never becomes `pass` · CONFIRMED requires every must-requirement to pass.
