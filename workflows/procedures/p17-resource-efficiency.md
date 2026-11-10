# P17 — Efficient resource utilization

## Trigger
- Tokens, tool calls, time or money are limited or being measured, or
- you notice repeated reads, repeated searches or long outputs that nobody needs, or
- you are choosing which model or agent should do a piece of work.

## Inputs
- The budget, if stated: maximum cost, time, calls or context.
- The mode in use and the work remaining.
- The models and tools available and their relative cost.

## Protocol
1. **Match effort to the mode.** FAST gets a handful of calls; STANDARD tens; DEEP and AUTONOMOUS spend on investigation and verification, not on prose. If the effort no longer matches the mode, change the mode.
2. **Take the cheapest action that yields ground truth.** A search before a read; a ranged read before a whole file; one test before the whole suite; then the whole suite once at the end.
3. **Do not pay twice.** Write a fact down the first time you learn it. Do not re-read a file you just wrote, re-run a search you already ran, or re-derive a decision already recorded.
4. **Parallelize independent read-only work** in a single step. Keep dependent work sequential.
5. **Keep bulky material out of the main context.** Delegate wide exploration to a subagent that returns conclusions; send long outputs to a file and read the part you need.
6. **Assign the model by the difficulty of the unit.** Ambiguous planning, architecture and review: the strongest model. Well-specified, checkable implementation: a smaller, cheaper one. Never save money on verification.
7. **Cut waste in the output.** No restating the request, no narration of steps, no repeated summaries. The delivery block is the summary.
8. **Stop when done.** When the acceptance checks pass and the report is written, the task ends. Extra unrequested work is cost without mandate.
9. **Never trade away correctness.** Skipping the check that proves the result is not efficiency; it moves the cost to the user.

## Tools
- Search and ranged reads; filters on command output.
- Subagents with a smaller model for mechanical units.
- Host features that report usage (token counters, cost output) to measure rather than guess.
- `scripts/select_mode.py` to sanity-check the effort level.

## Outputs
- The same deliverable, produced with fewer calls and less context.
- When the user asked about cost: a short usage note with measured numbers.

## Verification
- No identical tool call appears twice without a reason.
- The acceptance checks were still run in full.
- The effort spent is in line with the mode's budget, or the mode was changed and noted.
- Reported savings come from measurements.

## Recovery
- **Budget nearly spent with work remaining:** stop, checkpoint, deliver what is verified as PARTIAL, and list the remaining work in priority order.
- **You optimized away a needed step:** restore it. Record the lesson in the failure log if the project keeps one.
- **Context is overflowing:** follow `p09-context-management` — checkpoint, drop finished detail, reload only what the next step needs.
- **A cheap model keeps failing a unit:** escalate that unit to a stronger model with the failure evidence; do not loop.
