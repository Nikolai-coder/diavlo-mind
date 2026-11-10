# Review request

Give the reviewer the requirements and the artifact — nothing about how it was made.

```
TASK PACKET
id: <id>
role: reviewer
mode: <mode>
objective: Find defects, missing requirements, needless complexity and risks in the work below.
requirements:
  - R1: <text>
  - R2: <text>
context:
  - Conventions: <path to conventions file, if any>
inputs:
  - Changed files: <paths>   (or: the artifact at <path>)
  - How to read it: <entry point, what calls what>
constraints:
  - read-only: everything
deliverable: Verdict, findings table (severity, where, finding, why it matters, suggested fix), requirement coverage table, result packet.
acceptance:
  - Every requirement has a coverage row.
  - Every finding cites a file and line.
escalate_if:
  - The requirements are too vague to judge against.
```

Do **not** include: the author's explanation, the author's test results, or statements such as "this should be fine".
