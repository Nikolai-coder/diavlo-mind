# Architecture

How DIAVLO MIND is built and why. For how to use it, start with `README.md`; for installation, `INSTALL.md`.

## 1. Purpose and limits

**Goal.** Give a model a working method that makes its output more reliable: requirements pinned down, effort sized to the task, facts checked before use, results verified before they are reported, state written down so work survives a lost context.

**Not goals.**

- It does not copy weights, extract hidden reasoning, or reproduce any model's private chain of thought. Every procedure describes actions that can be observed from outside: read this, run that, write this down, report in this form.
- It does not claim that a small model becomes a large one. Instructions change what a model is asked to do, not what it is able to do.
- It is not a persona. Voice and language stay the model's and the user's.

## 2. Design principles

| Principle | Consequence in the design |
|---|---|
| Observable actions only | Every procedure has trigger, inputs, protocol, tools, outputs, verification and recovery. Nothing says "think harder". |
| Lightest thing that works | Four modes; FAST adds almost nothing. Agents are optional. Ceremony is treated as a cost. |
| Progressive disclosure | `SKILL.md` holds the core in about 3,000 tokens. Everything else is loaded only when its trigger applies. |
| Provider independence | The core is plain Markdown. Provider knowledge lives only in `adapters/` and in the provider functions of `scripts/dm_llm.py`. |
| One source of truth | The ten rules exist once, in `SKILL.md`; prompts and orchestrator read or copy them mechanically. The version exists once, in `VERSION`. |
| Evidence over assertion | Claims carry a level (VERIFIED, SOURCED, ASSUMED, UNKNOWN). The state tool refuses "done" without evidence. The benchmark scores overclaims. |
| Measured, not presumed | Changes to the framework go through the benchmark; the core rules are fingerprinted so they cannot change unrecorded. |

## 3. Layers

```
                 ┌──────────────────────────────────────────────────────────┐
  entry point    │ SKILL.md — ten rules · loop · mode table · routing table │
                 └──────────────┬───────────────────────────────────────────┘
                                │ loads on demand
        ┌───────────────────────┼─────────────────────────┬──────────────────────┐
        ▼                       ▼                         ▼                      ▼
 workflows/modes/        workflows/procedures/     workflows/protocols/      agents/
 4 effort profiles       20 situation playbooks    handoff · orchestration   8 role definitions
                                                   recovery · advisor ·
                                                   self-improvement
        │                       │                         │                      │
        └───────────────────────┴────────────┬────────────┴──────────────────────┘
                                             ▼
                      memory/ (templates, schemas)  ·  prompts/ (portable tiers, templates)
                                             │
                                             ▼
        scripts/ — state manager, packets, mode selector, provider client, orchestrator,
                   installer, validator, prompt builder, packager, improvement log, publisher
                                             │
                                             ▼
                 adapters/ — how the above reaches each environment
                 evaluation/ — tasks, hidden checks, harness, scoring, improvement record
```

### 3.1 Core (`SKILL.md`)

Three things every task needs: the **ten rules**, the **loop** (FRAME → SCOPE → GROUND → PLAN → BUILD → PROVE → DELIVER) and the **mode table**. Then a routing table that says which file to read in which situation. The rules sit at the top because hosts that compact context keep the beginning of a skill.

### 3.2 Modes (`workflows/modes/`)

| Mode | Adds |
|---|---|
| FAST | Nothing but one check and a one-line statement of it |
| STANDARD | Requirement list, short plan, executed checks, delivery block |
| DEEP | Investigation with evidence, options and decision record, tests, independent review |
| AUTONOMOUS | Persistent state, task graph, checkpoints, progress reports, definition of done |

Mode choice is a table lookup on explicit signals, and `scripts/select_mode.py` implements the same table so a person, a model and an external orchestrator reach the same answer.

### 3.3 Procedures (`workflows/procedures/`)

The twenty capabilities named in the project brief map one to one to procedure files:

| # | Capability | Procedure |
|---|---|---|
| 1 | Complex problem decomposition | `p01-decomposition.md` |
| 2 | Long-horizon task planning | `p02-long-horizon-planning.md` |
| 3 | Autonomous software engineering | `p03-software-engineering.md` |
| 4 | Tool selection and execution | `p04-tool-use.md` |
| 5 | Research and information verification | `p05-research-verification.md` |
| 6 | Architecture design | `p06-architecture-design.md` |
| 7 | Error identification and recovery | `p07-debugging-recovery.md` |
| 8 | Multi-agent coordination | `p08-multi-agent-coordination.md` |
| 9 | Context management | `p09-context-management.md` |
| 10 | Requirement tracking | `p10-requirement-tracking.md` |
| 11 | Quality assurance | `p11-quality-assurance.md` |
| 12 | Adaptive task execution | `p12-adaptive-execution.md` |
| 13 | Creative problem-solving | `p13-creative-problem-solving.md` |
| 14 | Engineering trade-off analysis | `p14-tradeoff-analysis.md` |
| 15 | Task completion verification | `p15-completion-verification.md` |
| 16 | Iterative improvement | `p16-iterative-improvement.md` |
| 17 | Efficient resource utilization | `p17-resource-efficiency.md` |
| 18 | Decision-making under uncertainty | `p18-decisions-under-uncertainty.md` |
| 19 | Independent verification | `p19-independent-verification.md` |
| 20 | Consistency across large projects | `p20-consistency-at-scale.md` |

Each file has the same seven sections — Trigger, Inputs, Protocol, Tools, Outputs, Verification, Recovery — and is self-contained, so loading one never requires loading another.

### 3.4 Roles (`agents/`)

Eight roles with separated powers:

| Role | Writes | Never |
|---|---|---|
| Orchestrator | Project state, integration | Marks work done on an agent's word |
| Architect | Design, contracts, conventions | Implements features |
| Planner | A proposed task graph | Changes files or task status |
| Executor | Only the paths in its packet | Redesigns, or delegates further |
| Researcher | Findings | Changes project files |
| Reviewer | Findings | Edits the work it reviews |
| Validator | Check results | Fixes what it tests |
| Optimizer | Only the paths in its packet | Keeps an unmeasured change |

The files are valid Claude Code subagent definitions (frontmatter plus system prompt). The body is plain text that any host can use as a role prompt; `scripts/install.py` converts them to Codex TOML and Gemini CLI agent files.

### 3.5 Protocols (`workflows/protocols/`)

- **Handoff** — task packet down, result packet up; same fields in text and JSON; schemas in `memory/schemas/`.
- **Orchestration** — team size by mode, ownership map, review triggers, the single-writer rule for state.
- **Recovery** — find state, verify it against the files, reconcile, re-anchor, continue.
- **Fable Advisor** — strong model for judgment, smaller model for execution, with escalation rules; and the independent mode with its compensations.
- **Self-improvement** — failure → cause category → one change → benchmark → keep or reject, recorded.

### 3.6 State (`memory/`, `scripts/dm_state.py`)

State lives in the user's project under `.diavlo-mind/`, never in the skill folder. `state.json` holds objective, definition of done, requirements, tasks with dependencies, decisions and checkpoints. The tool enforces the rules that matter: no start before dependencies finish, no `done` without evidence, no `dropped` without a reason, a warning after two failed attempts, cycle and coverage checks, and a `done-check` that exits 0 only when everything is proven.

### 3.7 Tooling (`scripts/`)

| Script | Purpose | Calls a model |
|---|---|---|
| `select_mode.py` | Mode recommendation from explicit signals | No |
| `dm_state.py` | Project state, queue, checkpoints, resume, done-check | No |
| `dm_packet.py`, `dm_schema.py` | Create, validate and render packets | No |
| `dm_llm.py` | One completion function over eight back ends | Yes |
| `dm_orchestrate.py` | Planner → executor → check → repair → reviewer for chat-only models | Yes |
| `install.py` | Install into Claude Code, Codex, Gemini CLI, Antigravity or any skills folder | No |
| `build_prompts.py` | Sync rules and version into the prompt tiers; build the full bundle | No |
| `validate.py` | Whole-repository validation | No |
| `package.py` | Release archives | No |
| `dm_improve.py` | Failure records, decisions, core-rules lock | No |
| `publish_github.py` | Create the GitHub repository, push, set description and topics | No |

All are Python 3.9+ with the standard library only, so they run in restricted sandboxes and on Windows without setup.

### 3.8 Evaluation (`evaluation/`)

Eight tasks, one per category in the brief, each with a prompt, a seeded workspace, hidden checks and a reference solution. The harness runs a task in a temporary directory outside the repository, with and without the framework, then runs the hidden checks and records success, requirement coverage, unresolved errors, overclaims, tokens, cost, turns and tool calls. `selftest.py` proves the checks discriminate without calling any model.

## 4. Key decisions

**D1 — The repository root is the skill.**
Options: skill in a subfolder with a separate plugin wrapper; or `SKILL.md` at the root. Chosen: root. One `git clone` into a skills folder is then a complete install, and Claude Code loads the same folder as a plugin with its agents. Cost: a full clone carries the benchmark and tests into the skills folder (unused unless read); the installer offers a lean copy. Revisit if a host starts loading every file of a skill eagerly.

**D2 — Twenty separate procedure files, not one manual.**
Options: one long reference; or one file per procedure. Chosen: one per procedure, routed from `SKILL.md`. A model loads about 500 words for the situation at hand instead of about 10,600. Cost: twenty files to keep consistent, which the validator checks (sections present, each listed in `SKILL.md`). Revisit if hosts stop supporting on-demand file reads.

**D3 — Packets are plain text first, JSON second.**
Options: JSON only; text only; both with the same fields. Chosen: both. Small models produce the text form more reliably; scripts need JSON. Cost: two renderings to keep aligned, done by one renderer in `dm_packet.py`.

**D4 — The orchestrator uses no tool calling.**
Options: implement each provider's function-calling protocol; or exchange whole files as marked text. Chosen: marked text. It works with every chat model, needs one wire format per provider instead of three, and the model never executes anything — only the user's own check command runs. Cost: whole files travel in every call, which limits workspace size; weak models sometimes break the markers, which the orchestrator reports rather than writes. Revisit for large repositories.

**D5 — Standard library only.**
Options: use SDKs and a YAML library; or none. Chosen: none. The scripts then run inside sandboxes without network access and on any machine with Python. Cost: a small JSON-schema subset validator and hand-written HTTP calls, both covered by tests against a local mock server.

**D6 — The ten rules are locked.**
Options: trust review; or fingerprint the rules. Chosen: fingerprint in `evaluation/improvement/core-rules.lock.json`, checked by the validator and CI. A change needs `dm_improve.py approve-core-change --reason …`, which writes the reason into the improvement log. Cost: one extra command for a legitimate change.

**D7 — The benchmark hides its checks and keeps workspaces outside the repository.**
Options: visible tests; or hidden checks run after the fact. Chosen: hidden. Visible tests measure test-following; hidden checks measure whether the requirements were actually met and whether the completion claim was true. Cost: checks must be validated separately, which `selftest.py` does with a do-nothing run and a reference run.

## 5. What is implemented, what is verified, what is proposed

**Implemented** — present in this repository as files that run or can be loaded:
everything listed in section 3.

**Verified** — executed in the build environment, with the evidence kept:

| Claim | Evidence |
|---|---|
| The repository is internally consistent | `python scripts/validate.py` |
| Every script behaves as documented | `python -m unittest discover -s tests` |
| The benchmark checks discriminate | `python evaluation/selftest.py` |
| The skill, the plugin and the marketplace manifest load in Claude Code | `claude plugin validate`, `claude plugin list`, `claude plugin details`, recorded in `adapters/claude-code.md` |
| The skill is followed in a live session and its report matches reality | `examples/01-claude-code-skill/` |
| The hybrid orchestrator works with two different live models | `examples/02-fable-advisor-orchestrator/` |
| Measured effect of the framework on two small models | `evaluation/results/RESULTS.md` |

**Not verified** — implemented from documentation, not executed here:
the Claude API, OpenAI API and Gemini API calls against the live services (checked against a local mock only); installation in Codex, Gemini CLI, Antigravity, ChatGPT and claude.ai; Windows and macOS.

**Proposed** — described but not built:
a tool-calling agent loop for the API adapters; rubric-based judging of architecture and creative quality (rubrics exist in `evaluation/rubrics/`, no scores were produced); hooks that enforce rules mechanically in Claude Code.

## 6. Extending

| To add | Do this | Then |
|---|---|---|
| A procedure | New file in `workflows/procedures/` with the seven sections; add a row to the routing table in `SKILL.md` | `python scripts/build_prompts.py && python scripts/validate.py` |
| A role | New `agents/dm-<role>.md` with the required sections; add it to `ROLES` in the scripts that list roles | Run the tests |
| A provider | One function in `scripts/dm_llm.py` and a test against the mock server | Document it in an adapter with its verification status |
| A benchmark task | New folder in `evaluation/tasks/` with `task.json`, prompt, `checks/check.py`, `reference/` | `python evaluation/selftest.py` |
| A change to the ten rules | Edit `SKILL.md`, rebuild the prompts, run the benchmark before and after, then `dm_improve.py approve-core-change` | Bump the major version |
