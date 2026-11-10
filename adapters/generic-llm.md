# Adapter: generic LLM agents

For everything else: local models, OpenAI-compatible servers, agent frameworks, and chat windows with a single instruction field. The universal core is plain text, so any model that can follow written instructions can use it.

**Verification status.** The `compatible`, `cmd` and `claude-cli` providers of `scripts/dm_llm.py` are covered by the test suite; `claude-cli` was also run against a live model on 2026-11-10 (see `examples/`). No third-party local server was run in the build environment.

## Installation

Choose by what your environment can do.

**A. One instruction field** — paste a prompt tier.

| Tier | File | Size | Use when |
|---|---|---|---|
| Micro | `prompts/system/diavlo-mind-micro.md` | under 1,500 characters | The field is tiny, or the context window is small |
| Compact | `prompts/system/diavlo-mind-compact.md` | under 8,000 characters | Default for chat tools and small models |
| Standard | `prompts/system/diavlo-mind-standard.md` | about 14,000 characters | Agents with tools; API system prompts |
| Full | `prompts/system/diavlo-mind-full.md` | about 180,000 characters | Large-context models, or as an attached reference document |

**B. An agent host that reads Agent Skills** — copy the folder into its skills directory.

```bash
python scripts/install.py custom --dest /path/to/skills      # creates /path/to/skills/diavlo-mind
python scripts/install.py agents                             # ~/.agents/skills/diavlo-mind, read by several tools
```

**C. An OpenAI-compatible server** (local or hosted) — use the orchestrator.

```bash
export DM_OPENAI_BASE_URL=http://localhost:11434/v1      # your server's /v1 endpoint
python scripts/dm_orchestrate.py --task task.md --workspace ./project --mode standard \
  --executor compatible:<model-name> --check-cmd "python -m pytest -q"
```

Set `DM_OPENAI_API_KEY` if the server wants a key.

**D. Any command-line model** — anything that reads a prompt on standard input and prints the reply.

```bash
export DM_CMD="my-model-cli --no-stream"
python scripts/dm_orchestrate.py --task task.md --workspace ./project --mode fast --executor cmd:local
```

**E. No scripts at all** — run the roles by hand. Paste the body of `agents/dm-planner.md` and the task; paste the plan and the body of `agents/dm-executor.md`; then start a fresh chat with `agents/dm-reviewer.md`, the requirements and the result only. Use the packet formats in `workflows/protocols/handoff.md`.

## Available features

| Feature | A: pasted tier | B: skill folder | C/D: orchestrator | E: by hand |
|---|---|---|---|---|
| The ten rules, loop and modes | Yes | Yes | Yes | Yes |
| Progressive disclosure | No | If the host implements it | No | You choose what to paste |
| Files and tests | Only with the host's tools | Host's tools | Workspace directory and your `--check-cmd` | You run them |
| Separate reviewer context | No | Host-dependent | Yes | Yes, a fresh chat |
| Advisor and executor on different models | No | Host-dependent | Yes, any two providers | Yes |

## Tool integration

- **The host has tools.** Map the tool kinds named in the procedures — search, read, edit, run, browse, delegate — to what exists. Leave out what does not; the framework tells the model to report NOT RUN rather than pretend.
- **The host has no tools.** Use the orchestrator. Its protocol is plain text: the model writes each file in full between `=== FILE: path ===` and `=== END FILE ===`, and deletes with `=== DELETE: path ===`. The orchestrator refuses paths outside the workspace and never executes anything the model wrote; it runs only the check command you gave it.
- **An agent framework.** Give each role file (the text after the frontmatter) to one agent as its system instructions; use the task and result packets as the message format between agents; let only the orchestrator role write shared state.

## Model configuration

- Pick the tier by context window: the instructions should stay well under a tenth of it.
- Small models follow short, concrete instructions better than long ones. Start with the compact tier and add only the procedures a task needs.
- For the hybrid setup pass two specs: `--advisor <provider>:<strong model> --executor <provider>:<small model>`. Providers can differ.
- The scripts send no sampling parameters. Set them in your server if you want determinism.
- Timeouts: `DM_HTTP_TIMEOUT` (seconds, default 600).

## Supported execution modes

| Mode | A: pasted tier | C/D: orchestrator | E: by hand |
|---|---|---|---|
| FAST | Yes | `--mode fast` | Yes |
| STANDARD | Yes | `--mode standard` | Yes |
| DEEP | Partly: one context for all roles | `--mode deep` | Yes |
| AUTONOMOUS | Only if state is kept in files you carry | Per run; wrap with `scripts/dm_state.py` | Yes, with the templates in `memory/templates/` |

## Environment limitations

- Instructions do not add capability. A model that cannot solve a problem alone will usually not solve it because it was told to plan first. What the framework improves is process: fewer dropped requirements, fewer unverified claims, fewer loops. Measure the effect on your model with `evaluation/`.
- Small context windows cannot hold the standard tier plus a real task. Use micro or compact there.
- Weak models may not follow the file-marker protocol reliably. The orchestrator reports unclosed or unsafe blocks instead of writing them; if that happens often, the model is too small for unattended file work.
- The orchestrator sends the workspace's text files with every call. Keep the workspace small or point it at a subdirectory.
- Nothing here sandboxes your check command. It runs with your permissions.
