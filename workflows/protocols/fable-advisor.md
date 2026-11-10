# Fable Advisor mode — strong model as architect, smaller models as executors

An optional hybrid setup. The strongest model available (for example Claude Fable 5.2) handles the difficult judgment — framing, architecture, planning, review, hard escalations. Smaller, cheaper models execute well-defined units. DIAVLO MIND also runs fully without an advisor; the second half of this file describes that mode and the differences.

"Advisor" below means whichever model is strongest in your setup. Nothing here depends on a specific vendor.

## Role assignment

| Role | Advisor mode | Independent mode |
|---|---|---|
| Orchestrator | Advisor | The single model |
| Architect | Advisor | The single model |
| Planner | Advisor, or executor model reviewed by advisor | The single model |
| Executor | Executor model | The single model |
| Researcher | Executor model for gathering; advisor for conflicting or decisive evidence | The single model |
| Reviewer | Advisor | The single model in a fresh context |
| Validator | Executor model (runs checks; judgment is minimal) | The single model in a fresh context |
| Optimizer | Executor model, with the advisor choosing targets | The single model |

## Protocols

### 1. Task delegation
The advisor writes one task packet per unit (`workflows/protocols/handoff.md`). For a smaller executor the packet must be tighter than for a peer:

- one unit, one or two files, one check;
- the relevant code or text is quoted or pointed to exactly — not "see the codebase";
- interfaces are given as signatures or examples, not described;
- the acceptance check is a command or a precise inspection;
- `escalate_if` lists the specific surprises that should stop the executor.

If a packet cannot be made this precise, the unit is not ready to delegate: split it, or keep it with the advisor.

### 2. Structured handoffs
Executors return result packets. The advisor does not accept prose instead of a packet, and does not accept `status: DONE` without evidence lines.

### 3. Intermediate verification
After each executor result, before any dependent unit starts:

1. A validator (executor-class model is enough) runs the acceptance checks.
2. The orchestrator compares `changes` with the packet's writable paths.
3. On failure the result goes back with the check output attached.

The advisor reads code only when a check fails twice, at milestones, and at final review. That is where the cost saving comes from.

### 4. Escalation of difficult problems
An executor escalates — returns BLOCKED or FAILED with evidence — when:

- an `escalate_if` condition fires;
- the same acceptance check failed twice;
- the unit needs a design decision the packet did not make;
- the unit needs a file outside its writable paths;
- requirements appear to conflict.

The advisor then does one of: answer and resend a corrected packet; split the unit; take the unit itself; or change the design. A third blind retry by the executor is never the answer.

### 5. Architectural review
The advisor reviews at fixed points, not continuously:

- the plan before execution starts,
- interface contracts before units that depend on them start,
- each milestone's integrated result,
- any change to a frozen interface or to the conventions file.

### 6. Final integration
The advisor (as orchestrator) merges, runs or commissions the full integration checks, performs the final review against the requirements, and writes the delivery report. The report states which model did which role.

## Cost and quality expectations

- Advisor tokens go to short, high-leverage outputs: packets, decisions, findings. Executor tokens go to bulk work.
- Savings depend on how well units are specified. Vague packets cause retries that cost more than doing the work in the advisor.
- Measure it. `evaluation/README.md` describes how to compare an executor alone, an executor with DIAVLO MIND, and the hybrid setup on the same tasks. Do not assume a gain you have not measured.

## Setups

**Claude Code** — run the main session on the strongest model and let executors use a smaller one:

```
python scripts/install.py claude-code --executor-model haiku --advisor-model inherit
```

This installs the skill with its role agents set to `model: haiku` for executor, researcher, validator and optimizer, and `model: inherit` (the session's model) for architect, planner, reviewer and orchestrator. Use whatever aliases or ids your Claude Code version accepts in the subagent `model` field.

**Any API** — `scripts/dm_orchestrate.py` takes separate models for the two classes:

```
python scripts/dm_orchestrate.py --task task.md --workspace ./proj --mode deep \
  --advisor anthropic:<strong-model-id> --executor anthropic:<small-model-id> \
  --check-cmd "python -m pytest -q"
```

Providers can be mixed (for example an advisor from one vendor and a local executor). See `adapters/`.

## Independent mode — no advisor available

Everything in DIAVLO MIND works with a single model. What changes:

| Aspect | Advisor mode | Independent mode |
|---|---|---|
| Who plans and reviews | A stronger model | The same model, in a separate fresh-context pass |
| Source of independence | Different model and fresh context | Fresh context only |
| Escalation target | The advisor | A different approach, then the user |
| Packet precision needed | High (executor is weaker than planner) | Moderate (same capability on both sides) |
| Main risk | Under-specified packets, retry cost | Shared blind spots between author and reviewer |
| Ceiling on difficulty | Set by the advisor for design, by the executor for implementation | Set by the single model throughout |

Compensations to apply in independent mode:

1. **Externalize more.** Requirements, plan and decisions go to files earlier, because no stronger model will catch a dropped requirement.
2. **Lean on executable checks.** Tests and commands are the reviewer that does not share the author's blind spots.
3. **Cold-read review.** The review pass gets only requirements and artifact (`workflows/procedures/p19-independent-verification.md`).
4. **Smaller steps.** Prefer more, smaller units with a check each over large units.
5. **Earlier honest stops.** When two approaches have failed, report with evidence instead of producing a confident guess.

Independent mode cannot raise a model above its own ability on problems that need insight it lacks. It reliably helps with the failures that come from process: missed requirements, unverified claims, loops, scope creep and lost state.
