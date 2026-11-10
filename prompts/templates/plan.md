# Plan

```
Objective: <testable outcome>
Mode: <mode> — <reason>
Definition of done:
  - <check>

Requirements: R1 <…> · R2 <…> · R3 <…>

Steps:
| # | Step | Output | Check | Depends on | Covers |
|---|------|--------|-------|------------|--------|
| 1 | <riskiest unknown first> | <artifact> | <command or inspection> | — | R1 |
| 2 | … | … | … | 1 | R2 |

Not doing: <explicit exclusions>
Assumptions: <each, with what would falsify it>
Re-plan if: <observations that make this plan wrong>
```

Rules: every step has a check that can fail · every requirement appears in "Covers" · update this file when the plan changes, with a one-line reason.
