# Delegation packet (task packet)

Send exactly this structure when handing work to another agent. Field rules are in `workflows/protocols/handoff.md`.

```
TASK PACKET
id: <task id>
role: <architect | planner | executor | researcher | reviewer | validator | optimizer>
mode: <FAST | STANDARD | DEEP | AUTONOMOUS>
objective: <one sentence — the outcome>
context:
  - <fact or pointer the agent needs> (<where it comes from>)
requirements:
  - R1: <text copied from the ledger>
constraints:
  - may write: <paths>
  - read-only: <paths, or "everything else">
  - <other limits>
inputs:
  - <files, data, earlier results>
deliverable: <what to hand back, in what form>
acceptance:
  - <check that defines done>
escalate_if:
  - <condition that should stop the agent>
budget: <optional>

Return a RESULT PACKET (status, summary, deliverables, evidence per requirement,
changes, issues, assumptions, open_questions, next).
```

Checklist before sending:

- [ ] One unit of work, one owner.
- [ ] Nothing in it depends on having seen this conversation.
- [ ] Writable paths do not overlap with any other packet in flight.
- [ ] Every requirement has an acceptance check.
- [ ] For a reviewer or validator: the author's reasoning and reported results are **not** included.
