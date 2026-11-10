# Orchestration protocol — running several agents on one objective

Use this when more than one agent role is involved. For single-agent work, ignore it.

## Decide how many agents

| Situation | Team |
|---|---|
| FAST, or STANDARD with a small change | None. One agent does everything. |
| STANDARD with a risky change | Main agent + one Reviewer with fresh context. |
| DEEP | Main agent as Orchestrator + Researcher and Architect as needed + Reviewer + Validator. |
| AUTONOMOUS | Orchestrator + Architect + Planner + Executors + Reviewer + Validator; Researcher and Optimizer on demand. |

More agents mean more cold starts, more tokens and more coordination. Add an agent only when it removes more work than it creates.

## Roles and who may do what

| Role | Reads | Writes | Decides |
|---|---|---|---|
| Orchestrator | Everything | Project state, integration | Task order, assignments, when to stop |
| Architect | Requirements, code | Design, contracts, conventions | Structure and standards |
| Planner | Requirements, design | Task list (proposed) | Decomposition and order |
| Executor | Its packet, the files it owns | Only the files named in its packet | How to implement its unit |
| Researcher | Sources | Findings only | What the evidence supports |
| Reviewer | Requirements, artifact | Findings only | Severity of defects |
| Validator | Requirements, artifact | Check results only | Pass or fail per requirement |
| Optimizer | Artifact, measurements | Only the files named in its packet | Which measured change to keep |

The Orchestrator is the only writer of task status. Reviewers, Validators and Researchers do not change the work they examine.

## Pipelines

### DEEP

```
Orchestrator: FRAME → requirements, acceptance criteria
   ├─ Researcher (parallel, as needed) → findings with sources
   ├─ Architect → options, decision, contracts
Orchestrator: PLAN → tasks with checks
Orchestrator or Executor: BUILD, one task at a time, one check each
Reviewer (fresh context) → findings          ┐ both receive requirements + artifact only
Validator (fresh context) → pass/fail table  ┘
Orchestrator: fix blockers → re-validate → DELIVER
```

### AUTONOMOUS

```
Phase 0  Orchestrator: charter, definition of done, requirements → state
Phase 1  Architect: design + CONVENTIONS      Planner: task graph → state
Phase 2  loop:  next ready tasks
                → task packets → Executors (parallel only on disjoint files)
                → result packets → Orchestrator verifies acceptance → state
                → at each milestone: integration checks, Reviewer, Validator, checkpoint
Phase 3  Validator: full definition of done   Reviewer: whole-project pass
Phase 4  Orchestrator: delivery report        Optimizer: only if a target is unmet
```

## Assigning by capability

- Ambiguous or high-consequence work — framing, architecture, planning, review — goes to the strongest model available.
- Well-specified, checkable work — implementation, mechanical edits, running checks — can go to a smaller model.
- A unit that a smaller model fails twice is escalated with the failure evidence, not retried a third time.
- With one model only, every role still runs; independence then comes from fresh context rather than a different model.

Model assignment for hybrid setups is described in `workflows/protocols/fable-advisor.md`.

## Preventing conflicting modifications

1. Build an **ownership map** before parallel work: path or glob → agent. No overlaps.
2. Shared files (dependency manifests, registries, indexes, changelogs) have one owner. Others request changes through `issues` in their result packet.
3. Where the host supports it, give parallel writers separate branches or worktrees and merge in the Orchestrator.
4. Interfaces between units are written and frozen before the units start. Changing a frozen interface is an Architect decision and restarts the affected packets.
5. After merging, run the integration checks on the whole. Parts that pass alone can still fail together.

## Triggering reviews

A review is mandatory:

- before delivery in DEEP and AUTONOMOUS,
- at every milestone in AUTONOMOUS,
- after any change touching authentication, payments, permissions, data deletion or public interfaces,
- when an Executor returns DONE with assumptions that affect behaviour.

A review is skipped for FAST work and for mechanical changes fully covered by automated checks.

## Tracking state

In AUTONOMOUS mode the Orchestrator keeps `.diavlo-mind/state.json` through `scripts/dm_state.py`:

```
dm_state.py next                               # ready queue
dm_state.py task set T7 --status doing
dm_state.py task set T7 --status done --evidence "pytest -q → 15 passed"
dm_state.py task set T9 --status blocked --note "needs API key"
dm_state.py checkpoint "M2 complete" --next "start T12"
```

Status values: `todo`, `doing`, `review`, `done`, `blocked`, `dropped`. A task is `done` only with evidence. A `dropped` task needs a reason.

## Communication rules

- Agents talk through packets, not through shared memory of a conversation.
- Findings, assumptions and open questions travel upward in every result packet; the Orchestrator records them.
- Disagreements between agents are settled by a check both accept, or by the user — not by the last agent to speak.

## Hosts without subagents

Run the roles in sequence in one session, or with `scripts/dm_orchestrate.py` over an API. Write each packet and each result to a file. For the review pass, start from the requirements and the artifact only. This keeps the structure and most of the benefit; it does not give true parallelism or a truly independent reviewer, and the report must say so.

## When not to orchestrate

If you are writing packets longer than the work they describe, or the units keep needing each other's context, collapse back to a single agent in STANDARD or DEEP mode.
