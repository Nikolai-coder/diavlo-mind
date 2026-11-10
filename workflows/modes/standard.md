# STANDARD mode

For moderate programming, research and creative tasks. Structured planning and essential verification.

## Entry conditions

- A few steps or a few files, inside one component.
- Some investigation is needed, but the acceptance criteria are clear or can be stated in a few lines.
- No irreversible operation, no unknown root cause, no architecture decision. Any of those means DEEP.

## Workflow

1. **FRAME** — Write the objective in one sentence and the requirement list (R1…Rn). Add implied requirements that would embarrass you if broken (existing tests keep passing, file formats stay valid, public names unchanged). For each requirement note the check that will prove it.
2. **SCOPE** — State `Mode: STANDARD` and the reason in one line. If a requirement is ambiguous and a wrong reading would waste the work, ask one question now; otherwise record the assumption and go on.
3. **GROUND** — Read the files you will touch and the ones that call them. Run the existing tests or the current command once to get a baseline. For research, open primary sources. Write down only facts that change the plan.
4. **PLAN** — Three to seven steps. Each step names its output and its check. Put the step most likely to break the plan first.
5. **BUILD** — Execute step by step. After each step run its check. A failing check is fixed before the next step starts.
6. **PROVE** — Run all acceptance checks again from a clean start. Walk the requirement list against the artifact itself, not against your memory of it. Then do the self-review below.
7. **DELIVER** — Use the delivery format from `SKILL.md`.

## Self-review checklist (step 6)

- Every R has a status and evidence, or is listed as not done.
- Nothing outside the task changed (diff or file list checked).
- No leftovers: debug output, temporary files, commented-out code, unresolved TODOs you added.
- The artifact opens, runs or renders the way the user will use it.
- Claims in the report match what was executed. Anything unexecuted says NOT RUN.

## Budget

- Roughly 10–40 tool calls. Plan and requirement list together stay under about 15 lines.
- No agents by default. One exception: a single fresh-context reviewer is worth it when the change is risky for its size (auth, money, data deletion, public API).

## Helpful procedures

`p03-software-engineering` for code · `p05-research-verification` for facts · `p10-requirement-tracking` when requirements exceed three · `p11-quality-assurance` to choose tests · `p15-completion-verification` before delivering.

## Escalate to DEEP when

- A check fails twice for reasons you cannot explain.
- The change spreads to a second component, a schema, or a public interface.
- You find conflicting requirements or evidence.
- Verification is impossible in this environment and the risk is not trivial.

## De-escalate to FAST when

The plan collapses to a single obvious step after grounding. Say so and finish.

## Example

Request: "Add a `--since DATE` filter to the export command and document it."

- R1 `--since` accepts `YYYY-MM-DD` · R2 rows older than the date are excluded · R3 an invalid date gives a clear error and exit code 2 · R4 README documents the flag · R5 (implied) existing tests still pass.
- Ground: read `export.py`, `test_export.py`, README section; run tests → 12 passed (baseline).
- Plan: parse and validate the flag → apply the filter → add 3 tests → update README → full test run.
- Deliver with the evidence table: `pytest -q` → 15 passed; `export --since 2024-13-01` → exit 2 with message; README diff shown.
