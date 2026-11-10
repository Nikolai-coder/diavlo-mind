# Rubric: architecture quality

The automated checks for `architecture-notifications` verify structure, internal consistency and respect for the constraints. They cannot tell a sound design from a hollow one. Use this rubric for that part. It is scored by a person, or by a judge model that is given the brief, the two deliverables and this rubric — never the name of the configuration that produced them.

Score each criterion 0, 1 or 2. Quote the passage that justifies the score.

| # | Criterion | 0 | 1 | 2 |
|---|---|---|---|---|
| A1 | **Idempotency (R3)** | Not addressed, or check-then-insert | Mechanism named, race not considered | Enforced where concurrent duplicates collide (unique constraint or equivalent), behaviour of a repeat request defined |
| A2 | **Retries and dead letters (R4)** | Missing | Backoff or dead letter described, not both | Schedule, attempt limit, dead-letter storage and replay path all defined |
| A3 | **Rate limiting (R5)** | Missing | Per-process limiter that breaks with several workers | Limit shared across all senders, behaviour when the limiter is unavailable stated |
| A4 | **Quiet hours (R2)** | Missing | Held notifications described, urgency or release not | Hold, release and urgent bypass defined, time zones considered |
| A5 | **Throughput argument (R7)** | Asserted without numbers | Numbers given without derivation | Capacity derived from stated assumptions and compared with the target |
| A6 | **Fit to constraints (C1–C3)** | A constraint is violated | Constraints respected but design sized for a larger setting | Design is as small as the constraints suggest; nothing extra |
| A7 | **Failure behaviour** | Not discussed | One failure mode discussed | Database down, provider down and worker crash each have a stated outcome |
| A8 | **Trade-offs** | Options are strawmen | Real options, weak reasons | Real options, the deciding criterion and the cost of the choice are stated |
| A9 | **Testability** | No test strategy beyond "write tests" | Tests listed by type | Each requirement has a named test or measurement |

**Total: 0–18.** Report the per-criterion scores, not only the total.

## Procedure

1. Blind the submissions: remove file metadata and anything that names the model or the arm.
2. Score every submission against the rubric before comparing any two of them.
3. For a judge model, run three independent judgements per submission and report the median and the spread. Where judgements differ by more than one point on a criterion, a person decides.
4. Report rubric scores next to, never instead of, the automated check results.

Status in this repository: the rubric is provided; no rubric scores have been produced or published with version 1.0.0.
