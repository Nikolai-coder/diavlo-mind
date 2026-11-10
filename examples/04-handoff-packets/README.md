# Example 04 — handoff packets

Three packets in JSON form, each with the text form produced by `scripts/dm_packet.py render`:

| File | What it is |
|---|---|
| `task-packet.json` / `.txt` | The orchestrator delegates task T1 to an executor: objective, context, requirements, writable paths, acceptance checks, when to stop |
| `result-packet.json` / `.txt` | The executor returns DONE with one evidence line per requirement and two issues it noticed outside its scope |
| `blocked-result-packet.json` / `.txt` | The same task returned BLOCKED: the data contradicts the packet, so the executor stops and asks instead of guessing |

```bash
python scripts/dm_packet.py validate examples/04-handoff-packets/*.json
python scripts/dm_packet.py render examples/04-handoff-packets/task-packet.json
```

The validator applies the rules a schema cannot express: an executor packet must name writable paths, a reviewer or validator packet must not, DONE needs a proof for every requirement and cannot rest on ASSUMED evidence or carry an open blocker, and BLOCKED must say what is needed.
