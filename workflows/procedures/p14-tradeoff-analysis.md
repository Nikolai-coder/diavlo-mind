# P14 — Engineering trade-off analysis

## Trigger
- Two or more real options exist and they differ in cost, risk or quality, or
- a choice will be expensive to reverse, or
- someone will ask later why it was done this way.

## Inputs
- The decision to be made, in one sentence.
- The drivers: requirements, constraints and priorities that the choice must serve.
- The candidate options.

## Protocol
1. **State the decision as a question** with a deadline or trigger: "Which storage do we use for job state, decided before task T3?"
2. **List the options,** always including *do nothing* or *keep the current way*, and the simplest thing that could work.
3. **Pick the criteria** from the drivers — typically correctness, effort, operational cost, performance, risk, reversibility, fit with what exists. Three to six, each with a weight of high, medium or low.
4. **Fill the table with evidence.** For each cell write what you know and its level (VERIFIED, SOURCED, ASSUMED). Measure when measuring is cheap; a small benchmark or prototype beats an argument.
5. **Mark reversibility.** A two-way door (easy to undo) can be decided quickly on thin evidence. A one-way door deserves the experiment.
6. **Look for a dominated option** — worse on every weighted criterion — and remove it. Look for a cheap hybrid that takes the best of two.
7. **Decide.** State the choice, the deciding criterion, and what you are giving up.
8. **Record what would change your mind:** the measurement or event that reopens the decision.
9. **Write it down** in a decision record and link it from the place where the choice is implemented.

## Tools
- `prompts/templates/decision-record.md`.
- Quick measurements: a timing loop, a size count, a prototype.
- Primary sources for limits and prices (`p05-research-verification`).

## Outputs
```
Decision: job state in SQLite (single file) instead of Redis
| Criterion (weight) | SQLite | Redis | Keep in memory |
| Survives restart (high) | yes — VERIFIED | yes — SOURCED | no |
| Ops cost (high) | none | new service to run | none |
| Throughput (low) | ~2k writes/s — VERIFIED locally | higher — ASSUMED | highest |
| Reversibility | easy: one module | easy | — |
Why: restart safety with no new service; throughput need is ~50/s.
Giving up: horizontal scaling of workers on separate hosts.
Revisit if: more than one worker host is required.
```

## Verification
- At least two real options plus the status quo were compared.
- Each high-weight cell carries evidence or is labelled ASSUMED.
- The chosen option satisfies every hard constraint.
- The record names what is sacrificed and what would reopen the choice.

## Recovery
- **The options are too close to call:** choose the more reversible or the simpler one and move on.
- **A key cell is ASSUMED and the door is one-way:** run the experiment before deciding.
- **New evidence contradicts the record:** reopen it explicitly, update the table, and note the change of decision with its date.
- **Stakeholders disagree on weights:** show how the choice flips under each weighting and ask the owner to pick the weighting, not the option.
