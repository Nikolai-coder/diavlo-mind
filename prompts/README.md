# prompts/

Reusable instructions and templates that work without any agent host: copy, paste, send.

## System instructions — `prompts/system/`

Four sizes of the same operating procedure. Each file is the prompt itself, with nothing to strip before pasting.

| File | Size | Contains | Use it for |
|---|---|---|---|
| `diavlo-mind-micro.md` | under 1,500 characters | The ten rules in one line each and the shape of the final report | "Custom instructions" fields, very small context windows |
| `diavlo-mind-compact.md` | under 8,000 characters | The ten rules in full, the loop, the four modes, evidence words, eight situation playbooks, the delivery block | Custom GPT instructions, project instructions, `AGENTS.md`, small models |
| `diavlo-mind-standard.md` | about 14,000 characters | Everything in compact, plus all twenty procedures in condensed form, the eight roles, both packet formats, long-project state and no-tool behaviour | API system prompts, `--append-system-prompt`, agents with tools |
| `diavlo-mind-full.md` | about 180,000 characters | `SKILL.md` followed by every mode, procedure, protocol, role and template, each under a `FILE:` heading | Large-context models; an attached reference document; search and retrieval |

Which one to pick: the smallest that your tasks need. Longer instructions cost tokens on every request and are followed less precisely by small models. `evaluation/` lets you measure the difference on your own model instead of guessing.

### Keeping them in sync

- The ten rules inside the compact, standard and full tiers are copied from `SKILL.md` by `scripts/build_prompts.py`. Edit them only in `SKILL.md`.
- The full tier is generated. Do not edit it.
- The micro tier is written by hand, because a 1,500-character paraphrase cannot be generated; the validator checks that it still has ten numbered rules and fits its limit.
- `python scripts/build_prompts.py --check` fails when anything is stale or over its size limit. It runs in CI.

## Task templates — `prompts/templates/`

Fill-in structures for the moments where wording matters.

| Template | When |
|---|---|
| `task-brief.md` | Before starting anything larger than a quick fix: objective, requirements, constraints, acceptance checks |
| `plan.md` | A plan whose every step has a check |
| `delegation-packet.md` | Handing a unit of work to another agent |
| `result-packet.md` | Returning delegated work, including failures |
| `research-brief.md` | Asking for research, and the shape of the findings |
| `debug-report.md` | Recording a diagnosis: symptom, hypotheses tested, root cause, fix, regression check |
| `review-request.md` | Asking for an independent review without leaking the author's reasoning |
| `validation-report.md` | The pass/fail table of an executed validation |
| `decision-record.md` | A decision with its alternatives and what would reopen it |
| `delivery-report.md` | The final report block |

Fields in angle brackets are for you to replace. Delete the rows you do not need; never leave a field filled with a guess.
