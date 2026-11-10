# Examples

Each example is the saved output of something that was actually run, with the command that produced it. Nothing here is an idealised transcript. Local paths were replaced by `<workspace>` and `<run-dir>`.

| Example | Shows | Model calls |
|---|---|---|
| [01-claude-code-skill](01-claude-code-skill/) | The skill installed in Claude Code, on a small feature request, with an independent check of the result | Real run, 2026-11-10 |
| [02-fable-advisor-orchestrator](02-fable-advisor-orchestrator/) | The hybrid setup through the bundled orchestrator: a strong model plans and reviews, an older small model writes the code | Real run, 2026-11-10 |
| [03-autonomous-project-state](03-autonomous-project-state/) | `scripts/dm_state.py` across a session break: requirements, task graph, refused shortcuts, checkpoint, resume, done-check | No model; script output |
| [04-handoff-packets](04-handoff-packets/) | Task and result packets in JSON and text form, including a BLOCKED return | No model; validated by `scripts/dm_packet.py` |

The same small project is used throughout: `01-claude-code-skill/project-before/`, a CSV export tool with four tests, and the request in `01-claude-code-skill/task.md`.
