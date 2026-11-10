# Result packet

Return exactly this structure when finishing delegated work — including when the work failed.

```
RESULT PACKET
id: <same id as the task packet>
role: <your role>
status: DONE | PARTIAL | BLOCKED | FAILED
summary: <up to five lines — outcome first>
deliverables:
  - <path, or the content itself>
evidence:
  - R1: met — VERIFIED — `<command>` → <result>
  - R2: unmet — <reason>
  - R3: not_verified — NOT RUN: `<exact command>`
changes:
  - <path> (created | modified | deleted)
issues:
  - <blocker | major | minor | note> — <where> — <what> — <suggested fix>
assumptions:
  - <anything decided without confirmation>
open_questions:
  - <what the orchestrator must answer>
next: <recommended next action>
```

Status rules:

- **DONE** — every acceptance check ran in this session and passed.
- **PARTIAL** — something is unmet or unverified; the evidence lines say what.
- **BLOCKED** — you need something to continue; `open_questions` says what and from whom.
- **FAILED** — the approach did not work; `summary` says what was tried and `next` gives the most informative experiment.
