# P12 — Adaptive task execution

## Trigger
- An observation contradicts an assumption the plan depends on, or
- a step took far more effort than expected, or
- the mode you chose no longer fits the work, or
- the user changed direction.

## Inputs
- The current plan and the mode in use.
- The new observation, stated as a fact with its source.
- Remaining budget and constraints.

## Protocol
1. **Pause at the step boundary.** Finish or roll back the current small step so the workspace is in a known state.
2. **Name what changed** in one sentence: "The plan assumed X; I observed Y (source)."
3. **Trace the impact.** Which planned steps rest on the broken assumption? Which finished steps need re-checking?
4. **Re-size the mode** with the table in `SKILL.md`:
   - escalate when a check failed twice, scope spread to more components, requirements conflict, an irreversible step appeared, or verification became unclear;
   - de-escalate when what remains is routine.
5. **Choose among four moves** and say which:
   - *adjust* — change the affected steps, keep the goal;
   - *spike* — run a small time-boxed experiment to remove the uncertainty before committing;
   - *re-scope* — deliver a smaller, verified result and list what is deferred;
   - *stop* — the goal is not reachable here; report why and what would make it reachable.
6. **Time-box exploration.** Decide in advance how many attempts or tool calls the experiment gets. When the box is spent, decide with what you have.
7. **Rewrite the plan where it lives** and note the reason. The plan on disk always matches what you are doing.
8. **Tell the user when the change matters to them:** a different deliverable, a new risk, more time or cost. One or two lines; no ceremony for internal adjustments.

## Tools
- The plan or state file; `scripts/select_mode.py` for a reproducible mode recommendation.
- Version control to return to a known state before changing direction.
- A scratch directory for spikes.

## Outputs
- An updated plan with a one-line change note.
- If relevant, a message to the user: what changed, what it affects, what you are doing about it.

## Verification
- The broken assumption is written down with its evidence.
- Every plan step still rests only on verified or explicitly ASSUMED facts.
- Finished steps affected by the change were re-checked.
- The mode stated matches the work now being done.

## Recovery
- **You adapted without recording it:** reconstruct the change note now; undocumented pivots are how requirements get lost.
- **Repeated re-planning with no progress:** the task is under-specified or beyond current means. Stop and present the smallest decision the user must make.
- **Sunk-cost pull** (keeping an approach because of the effort already spent): compare only future cost and likelihood of success for each option.
- **The spike was inconclusive:** choose the reversible option and proceed, labelling the assumption.
