# Debug report

```
Symptom: <exact error text and the command that produced it>
Expected: <what should have happened>
Reproduction: <one command, and how often it fails>
Environment: <OS, runtime and library versions that matter>

Hypotheses tested:
| # | Hypothesis | Test | Predicted | Observed | Verdict |
|---|------------|------|-----------|----------|---------|
| 1 | … | … | … | … | rejected |
| 2 | … | … | … | … | confirmed |

Root cause: <one sentence that explains every symptom>
Evidence: <the observation that confirms it>
Fix: <what changed, in which files>
Regression check: <test or command> — fails before the fix, passes after
Related places checked: <same pattern elsewhere>
Not resolved / unknown: <anything left>
```
