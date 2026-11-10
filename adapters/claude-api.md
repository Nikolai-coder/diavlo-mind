# Adapter: Claude API

The API has no file system, shell or memory of its own. DIAVLO MIND reaches a model there in three ways: as a system prompt, as an uploaded Agent Skill running in the code-execution container, or through the bundled orchestrator.

**Verification status.** The request shape used by `scripts/dm_llm.py` was checked against the Messages API reference on 2026-11-10 and exercised against a local mock that follows that shape (`tests/test_llm_and_orchestrator.py`). No request was sent to the live API from this repository's build: no API key was available. The Skills API steps follow the documentation and were not executed.

## Installation

**A. System prompt** — works with every model and needs nothing else.

```bash
curl https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2026-10-21" \
  -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
  -d "$(python3 - <<'EOF'
import json, pathlib
print(json.dumps({
    "model": "<model-id>",
    "max_tokens": 4096,
    "system": pathlib.Path("prompts/system/diavlo-mind-standard.md").read_text(encoding="utf-8"),
    "messages": [{"role": "user", "content": "Your task here"}],
}))
EOF
)"
```

Choose the tier by budget: `diavlo-mind-compact.md` (about 1,400 tokens), `diavlo-mind-standard.md` (about 3,500 tokens) or `diavlo-mind-full.md` (about 44,000 tokens, the whole framework in one document). The prompt is static, which makes it a good candidate for prompt caching.

**B. Agent Skill in the code-execution container.**

1. Build the upload archive: `python scripts/package.py` → `dist/diavlo-mind.zip` (`SKILL.md` at the top of a single folder, as the API requires).
2. Create the skill with the Skills API (`/v1/skills`) or in the Claude Console and note its id.
3. Reference it in a request together with the code-execution tool:

```json
{
  "model": "<model-id>",
  "max_tokens": 4096,
  "container": {"skills": [{"type": "custom", "skill_id": "skill_…", "version": "latest"}]},
  "tools": [{"type": "code_execution_20250825", "name": "code_execution"}],
  "messages": [{"role": "user", "content": "Your task here"}]
}
```

Pin a version id instead of `latest` in production. Reuse `container.id` from the previous response to keep files between turns, and resend the response when `stop_reason` is `pause_turn`.

**C. Bundled orchestrator** — planner, executor and reviewer as separate calls, with your own check command.

```bash
export ANTHROPIC_API_KEY=…
python scripts/dm_orchestrate.py --task task.md --workspace ./project --mode standard \
  --executor anthropic:<model-id> --check-cmd "python -m pytest -q"
```

## Available features

| Feature | A: system prompt | B: uploaded skill | C: orchestrator |
|---|---|---|---|
| The ten rules, loop and modes | Yes | Yes | Yes (in every role prompt) |
| Progressive disclosure | No, the tier is sent whole | Yes | No |
| Bundled scripts | No | Yes, inside the container | Runs on your machine |
| Files | Only what you send | Container files | Your workspace directory |
| Running your tests | No | In the container, with pre-installed packages only | Yes, your `--check-cmd` |
| Separate reviewer context | No (one conversation) | No | Yes |
| Advisor and executor on different models | Your code | Your code | `--advisor` and `--executor` |

## Tool integration

- **Client tools.** Define your own tools (`name`, `description`, `input_schema`) for reading files, writing files and running commands, and execute the `tool_use` blocks in your application. The procedures name tool *kinds*; map them to whatever you expose.
- **Server tools.** The code-execution tool gives the model a sandboxed container; route B uses it.
- **No tools.** Route C needs none: the model returns whole files between `=== FILE: path ===` and `=== END FILE ===` markers, and the orchestrator writes them and runs your check. The model never executes anything.

## Model configuration

- `model`: any id your account lists. Planning and review benefit most from the strongest model; implementation of well-specified units can use a smaller one.
- `max_tokens` is required. `scripts/dm_llm.py` sends 8,192 unless told otherwise.
- API version `2026-10-21` rejects `temperature`, `top_p` and `top_k`. The scripts never send them.
- Authentication: `Authorization: Bearer <key>`. For the older header set `DM_ANTHROPIC_AUTH=x-api-key` and `DM_ANTHROPIC_VERSION=2023-06-01`.
- Gateways and proxies: `DM_ANTHROPIC_BASE_URL`.

## Supported execution modes

| Mode | A: system prompt | B: uploaded skill | C: orchestrator |
|---|---|---|---|
| FAST | Yes | Yes | `--mode fast` |
| STANDARD | Yes; checks are NOT RUN unless your tools run them | Yes | `--mode standard` |
| DEEP | Partly: one context plays every role | Partly | `--mode deep`, reviewer in a fresh context |
| AUTONOMOUS | Only if your application stores the state | Within one container's lifetime | Per run; use `scripts/dm_state.py` around it for multi-session work |

## Environment limitations

- Nothing persists between requests unless your application stores it. Project state is your responsibility.
- Without tools the model cannot verify anything. The framework then requires it to write NOT RUN, and the status is at most PARTIAL.
- In the code-execution container a skill has no network access and cannot install packages. The bundled scripts need only the standard library.
- An upload must stay under 30 MB, a request can attach at most 20 skills, and a skill name cannot contain the reserved words `anthropic` or `claude`.
- Custom skills are not shared between surfaces: a skill uploaded to the API is not available in claude.ai or Claude Code, and the reverse.
- The documentation states that Skills are not covered by zero-data-retention arrangements.

## Sources

- Messages API: <https://platform.claude.com/docs/en/api/messages/create>
- API versions and the 2026-10-21 changes: <https://platform.claude.com/docs/en/api/versioning>
- Agent Skills overview: <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview>
- Skills with the API: <https://platform.claude.com/docs/en/build-with-claude/skills-guide>
