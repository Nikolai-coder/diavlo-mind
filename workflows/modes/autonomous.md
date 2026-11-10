# AUTONOMOUS PROJECT mode

For large projects with many files, systems or development stages. Everything in DEEP, plus persistent state so the work survives interruptions and can be shared between agents.

## Entry conditions (any one)

- More than about 15 tasks, or more than one session of work.
- Several systems or workstreams that can progress independently.
- The user asked for the project to run with minimal supervision.

## The state folder

All project state lives in `.diavlo-mind/` at the project root. Nothing important exists only in conversation.

| File | Content | Written by |
|---|---|---|
| `state.json` | Objective, mode, definition of done, requirements, tasks with dependencies and status, decisions, checkpoints | `scripts/dm_state.py` |
| `STATE.md` | Human-readable snapshot of the same data | `dm_state.py report` |
| `CONVENTIONS.md` | Names, structure, style, interfaces everyone must follow | Architect / Orchestrator |
| `DECISIONS.md` | Longer decision records when one line is not enough | Architect |
| `FAILURE_LOG.md` | Failures, cause category, fix, prevention | Whoever hit the failure |

Templates are in `memory/templates/`. If Python is unavailable, maintain the same files by hand.

## Workflow

### Phase 0 — Charter
1. Write the objective, scope and exclusions.
2. Write the **definition of done**: a short list of checks that, when all pass, end the project. Each must be runnable or inspectable.
3. Record requirements: `dm_state.py req add "<text>"`.
4. Agree the charter with the user if anything is ambiguous or irreversible. This is the one moment where asking is cheap.

### Phase 1 — Architecture and plan
1. Architect: structure, interfaces, standards → `CONVENTIONS.md` and decision records (`p06-architecture-design`).
2. Planner: tasks with dependencies, owner role, acceptance check and linked requirements → `dm_state.py task add …` (`p01-decomposition`, `p02-long-horizon-planning`).
3. Group tasks into milestones. Each milestone ends in something demonstrable.
4. Run `dm_state.py validate`: no dependency cycles, no dangling references, every requirement covered by a task.

### Phase 2 — Execution loop
Repeat until the queue is empty or a stop condition fires:

1. `dm_state.py next` → tasks whose dependencies are done.
2. Pick tasks. Parallelize only tasks that write different files.
3. For each: set `doing`, build a task packet, execute (directly or by delegating), receive the result packet.
4. Verify the result against the task's acceptance check. Passing → `done` with evidence. Failing → back to `todo` with a note; after two failures → `blocked` and escalate.
5. After each milestone: run integration checks, run a review, write a checkpoint and a progress report.

### Phase 3 — Integration and validation
1. Run the full integration suite from a clean checkout or clean directory.
2. Independent review of the whole against the requirements (`p19-independent-verification`).
3. `dm_state.py done-check` must exit 0: every requirement met with evidence, every task done or explicitly dropped with a reason.

### Phase 4 — Delivery
Delivery format from `SKILL.md`, plus: where everything is, how to run it, known limitations, and the exact next step for whoever continues.

## Checkpoints

Write a checkpoint (`dm_state.py checkpoint "<summary>" --next "<action>"`):

- after every milestone,
- before any risky or long operation,
- whenever context is getting full,
- before stopping for any reason.

A checkpoint states what changed since the last one, what is in progress, the next action, and open questions. A fresh session must be able to continue from the checkpoint and the files alone.

## Recovery from an interrupted session

1. `dm_state.py resume` → objective, last checkpoint, tasks in progress, ready tasks, open questions.
2. Verify the snapshot against reality: do the files and tests match what the state claims? Trust the files over the notes.
3. Any task left `doing` is re-verified: finish it, or reset it to `todo`.
4. Continue the execution loop. Details in `workflows/protocols/recovery.md`.

## Progress reports

`dm_state.py report` produces `STATE.md`. For the user, send a short report at each milestone: done since last report, current milestone status, blockers and decisions needed, next milestone. Counts, not adjectives: "14 of 22 tasks done, 31 tests passing, 2 blocked".

## Agents

The Orchestrator owns `state.json` and is the only writer of task status. Typical assignment: Architect and Planner once per phase, Executors per task, Researcher on demand, Reviewer and Validator per milestone, Optimizer only after correctness is proven. See `workflows/protocols/orchestration.md`.

## Stop conditions

Stop and report instead of continuing when:

- an irreversible or externally visible action needs approval,
- a requirement turns out to be infeasible or contradictory,
- a task is blocked after escalation,
- the budget the user set is exhausted,
- `done-check` passes — the project is finished.

## Completion criteria

The project is complete only when the definition of done is fully VERIFIED, `done-check` exits 0, and the final report lists every limitation. "Most of it works" is PARTIAL.
