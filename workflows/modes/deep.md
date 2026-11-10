# DEEP mode

For complex technical problems. Detailed investigation, architectural planning, implementation, testing and independent review.

## Entry conditions (any one)

- The root cause is unknown, or an earlier attempt already failed.
- The change crosses components, schemas or public interfaces.
- A design decision has real alternatives and long-lived consequences.
- A mistake could lose data, break security, cost money or be hard to reverse.
- Requirements or evidence conflict.

## Workflow

### 1. FRAME
Write the objective, the requirement list (R1…Rn) and explicit acceptance criteria. Separate *must* from *should*. Record what is out of scope. Keep these in a notes file (`NOTES.md` or `.diavlo-mind/`) so they survive context loss.

### 2. SCOPE
State `Mode: DEEP` and the trigger. Decide now whether a question to the user is blocking. Ask at most the questions whose answers change the design; batch them in one message.

### 3. GROUND — investigate before designing
- Map the relevant area: entry points, data flow, callers, tests, configuration, versions.
- Reproduce the problem, or measure the current behaviour, and save the exact command and output.
- List the assumptions the solution will rest on and verify each with a tool. Unverifiable ones stay labelled ASSUMED.
- Write findings as facts with sources. Stop investigating when new reads stop changing the picture.

Procedures: `p05-research-verification`, `p07-debugging-recovery`, `p09-context-management`.

### 4. PLAN — design, then schedule
- Produce at least two materially different options for each key decision, with a trade-off table and a recommendation (`p14-tradeoff-analysis`, `p06-architecture-design`).
- Record the decision in one short record: decision, alternatives, why, what would reverse it.
- Break the chosen design into tasks with dependencies and one check each (`p01-decomposition`). Put a thin end-to-end slice or the riskiest experiment first.
- Define the test strategy before writing code (`p11-quality-assurance`).

### 5. BUILD
- One task at a time, one check each. Commit or checkpoint after each passing task so any step can be rolled back.
- When reality contradicts the plan, stop and re-plan in writing (`p12-adaptive-execution`). Do not improvise around a broken assumption.
- After two failed attempts at the same step, step back: re-read the evidence and change approach (`p07-debugging-recovery`).

### 6. PROVE
- Run the full check suite from a clean state. Add a regression check for every defect found during the work.
- **Independent review** (`p19-independent-verification`): a reviewer with fresh context receives only the requirements and the artifact — not your reasoning — and tries to break it. Fix what it finds, then re-run the checks.
- **Validation**: a validator (or a separate pass) executes the acceptance checks and fills the requirement table itself.

### 7. DELIVER
Delivery format from `SKILL.md`, plus: the decision record, known limitations, and how to roll back.

## Agents in DEEP

Useful: Researcher (parallel fact-finding), Architect (options and contracts), Reviewer and Validator (independent pass). The Reviewer must not be the context that wrote the work. See `workflows/protocols/orchestration.md` for the pipeline and `workflows/protocols/handoff.md` for packets. Without subagents, do the review as a cold read: clear your working notes from view, re-read the requirements, then inspect the artifact as if someone else wrote it.

## Required artifacts

| Artifact | Purpose |
|---|---|
| Requirement list with acceptance criteria | Defines done |
| Investigation notes with sources | Makes the diagnosis checkable |
| Options and decision record | Makes the design reviewable |
| Task plan with checks | Makes progress measurable |
| Test or check output | Evidence |
| Review findings and their resolution | Independent confirmation |

## Budget

Effort follows risk, not word count. Spend it on investigation and verification; keep prose short. A DEEP report is usually under one page plus the evidence table.

## Escalate to AUTONOMOUS when

The task list exceeds about 15 items, work will outlive this session, or several workstreams must run in parallel.

## Stop and report (do not push on) when

- The requirement cannot be met with the tools or information available.
- Continuing requires an irreversible action that was not approved.
- Three distinct approaches failed. Report what was tried, the evidence, and the most promising next experiment.
