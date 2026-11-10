# P08 — Multi-agent coordination

## Trigger
- Units of work are independent enough to run in parallel, or
- a task would flood your context with material you only need the conclusion of, or
- finished work needs a reviewer who has not seen how it was made.

Do **not** use multiple agents for small tasks, for tightly coupled edits to the same files, or to look thorough.

## Inputs
- The unit list with dependencies (P01).
- The agents and models available, and what each can do (tools, context size, cost).
- The file ownership map: who may write what.

## Protocol
1. **Decide whether it pays.** Each delegation costs a cold start: the agent knows nothing you do not write down. Delegate when the unit is self-contained and the packet is cheaper to write than the work is to do.
2. **Assign by role and capability.** Planning, architecture and review go to the strongest model available; well-specified implementation can go to a smaller one. Role definitions are in `agents/`.
3. **Give every file one writer.** Before parallel work starts, list which agent owns which paths. Shared files (lockfiles, registries, indexes) get a single owner who applies everyone's changes.
4. **Write a task packet** for each delegation (`workflows/protocols/handoff.md`): objective, the context the agent needs, requirements, constraints and owned files, expected deliverable, acceptance checks, when to stop and escalate. Read it once as if you knew nothing else — would you know what to do?
5. **Fix the contracts first.** If two agents build sides of one interface, the interface is written down and frozen before either starts.
6. **Launch independent units together; run dependent ones in order.**
7. **Require a result packet** back: status, deliverables, evidence per requirement, files changed, issues, assumptions, open questions.
8. **Verify before integrating.** Run the acceptance check yourself. A result packet is a claim until checked.
9. **Integrate in one place.** The orchestrator merges, resolves conflicts and runs the integration checks. Agents do not merge each other's work.
10. **Keep one project state.** Only the orchestrator updates task status.

## Tools
- Native subagents where the host has them (Claude Code, Codex, Gemini CLI).
- `scripts/dm_orchestrate.py` for sequential orchestration over an API.
- `scripts/dm_packet.py` to create and validate packets.
- Version control branches or worktrees to isolate parallel writers.

## Outputs
- Ownership map.
- Task packets sent and result packets received.
- Integration result: what merged, what conflicted, what the integration checks showed.

## Verification
- No file was written by two agents.
- Every result packet's evidence was re-checked by the orchestrator or a validator.
- Integration checks pass on the merged whole, not just on each part.
- The task count delegated matches the task count integrated; nothing was dropped silently.

## Recovery
- **An agent returns PARTIAL or BLOCKED:** read its open questions, answer or re-scope, and resend a corrected packet. Do not finish its work silently in your own context without recording why.
- **Two agents produced conflicting changes:** the contract was underspecified. Fix the contract, pick one implementation, have the other adapt.
- **An agent ignored its boundaries:** discard the out-of-scope changes, tighten the packet's constraints, rerun.
- **Results are plausible but unverifiable:** treat as not done and send to the validator.
- **No subagents available:** run the roles one after another in the same session, writing each packet and result to a file so each pass starts from the written record rather than from memory.
