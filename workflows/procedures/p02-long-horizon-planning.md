# P02 — Long-horizon task planning

## Trigger
- The work spans several milestones, days or sessions, or
- more than one agent or person will contribute, or
- the unit list from P01 has more than about 15 items.

## Inputs
- Unit list with dependencies (P01).
- Constraints: deadline, budget, available tools and models, approvals required.
- Definition of done.

## Protocol
1. **Fix the end state.** Write the definition of done as a short list of runnable or inspectable checks. If the user has not given one, propose it and get agreement.
2. **Find the critical path.** The longest dependency chain decides the minimum duration. Units off that chain are candidates for parallel work.
3. **Cut milestones.** Each milestone ends with something demonstrable — a command that runs, a page that renders, a draft that reads end to end. Three to six milestones is typical. Milestone 1 is a walking skeleton: the thinnest version that exercises every layer.
4. **Front-load risk.** Schedule experiments for the biggest unknowns in milestone 1. A plan that discovers its main risk at the end is a bad plan.
5. **Estimate coarsely.** Label each unit S, M or L by how many separate checks it needs, not by time. An L unit must be split before it starts.
6. **Set checkpoints.** Decide when state is saved: at every milestone, before risky operations, and whenever context is nearly full.
7. **Write re-plan triggers.** List the observations that force a re-plan: a failed experiment, a requirement change, a unit failing twice, a milestone slipping past its budget.
8. **Publish the plan as a file** and keep it current. Status changes are recorded when they happen, not reconstructed later.

## Tools
- `scripts/dm_state.py` for the task graph, the ready queue and checkpoints.
- `memory/templates/PLAN.md` when keeping the plan by hand.
- Version control tags or commits at each milestone.

## Outputs
- Definition of done.
- Milestone table: goal, units, exit check, risk addressed.
- Critical path and parallelizable units.
- Checkpoint schedule and re-plan triggers.

## Verification
- Every unit belongs to exactly one milestone.
- Every milestone has an exit check that can fail.
- The biggest unknown is addressed in the first milestone.
- `dm_state.py validate` reports no cycles, no dangling dependencies and no uncovered requirements.

## Recovery
- **A milestone exit check fails:** the milestone is not done. Fix or re-plan; never move the check.
- **Scope grows:** add units, show the effect on the milestone list, and ask the user to choose between more time and less scope.
- **Progress stalls:** cut the next milestone to the smallest version that still demonstrates something, and deliver that.
- **Session interrupted:** follow `workflows/protocols/recovery.md`; the plan file and state are the source of truth, not memory.
