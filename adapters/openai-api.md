# Adapter: OpenAI API

For applications that call OpenAI models directly, through the Responses API or Chat Completions. The same instructions apply to any server that speaks the Chat Completions protocol.

**Verification status.** The request and response shapes used by `scripts/dm_llm.py` were checked against OpenAI's API reference on 2026-11-10 and exercised against a local mock that follows them (`tests/test_llm_and_orchestrator.py`). No request was sent to the live API: no key was available in the build environment.

## Installation

**A. Responses API** — put a prompt tier in `instructions`.

```bash
curl https://api.openai.com/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d "$(python3 - <<'EOF'
import json, pathlib
print(json.dumps({
    "model": "<model-id>",
    "instructions": pathlib.Path("prompts/system/diavlo-mind-standard.md").read_text(encoding="utf-8"),
    "input": "Your task here",
}))
EOF
)"
```

`instructions` applies to that one request, so send it every time.

**B. Chat Completions** — the same text as the first message, with role `developer`.

**C. Bundled orchestrator.**

```bash
export OPENAI_API_KEY=…
python scripts/dm_orchestrate.py --task task.md --workspace ./project --mode standard \
  --executor openai-responses:<model-id> --check-cmd "npm test"
```

Use `openai:<model-id>` for Chat Completions, and `--advisor` with a second model for the hybrid setup.

**D. Smoke test of your key and model.**

```bash
python scripts/dm_llm.py openai-responses:<model-id> "Reply with OK" --system "Be brief."
```

## Available features

| Feature | A/B: instructions | C: orchestrator |
|---|---|---|
| The ten rules, loop and modes | Yes | Yes |
| Progressive disclosure | No, the tier is sent whole | No |
| Files and tests | Only through tools you implement | Workspace directory and your `--check-cmd` |
| Separate reviewer context | Your code | Yes |
| Advisor and executor on different models | Your code | Yes |
| Token usage reporting | In the API response | Summed per role in the run report |

## Tool integration

With function tools the model can do the work itself. Define each tool with `type: "function"`, a `name`, a `description` and JSON-schema `parameters`; when the response contains a `function_call` item, run it and send back an item of type `function_call_output` with the same `call_id`. A minimal set that covers the procedures:

| Tool | Purpose | Guard |
|---|---|---|
| `read_file(path)` | Look before acting | Confine to the workspace |
| `write_file(path, content)` | Build | Confine to the workspace; refuse paths with `..` |
| `list_dir(path)` | Ground | Confine to the workspace |
| `run_command(command)` | Prove | Allow-list or sandbox; never run unreviewed commands on a machine that matters |

This repository does not ship that tool loop. Route C avoids tools entirely: the model returns whole files between marker lines, and only your own check command is executed. If you use an agent framework, give each file in `agents/` (the text after the frontmatter) to one agent as its instructions and use the packets in `workflows/protocols/handoff.md` for handoffs.

## Model configuration

- Any model id your account lists. Reasoning-capable models are the better choice for the planner and reviewer roles.
- The scripts send no sampling parameters and no token cap unless you pass `--max-tokens`; with Chat Completions the cap is sent as `max_completion_tokens`.
- Other endpoints: set `DM_OPENAI_BASE_URL`. For servers that expect the `system` role and `max_tokens`, use the `compatible:` provider described in `adapters/generic-llm.md`.

## Supported execution modes

| Mode | A/B: instructions | C: orchestrator |
|---|---|---|
| FAST | Yes | `--mode fast` |
| STANDARD | Yes; checks are NOT RUN unless your tools run them | `--mode standard` |
| DEEP | Partly: one context plays every role | `--mode deep` |
| AUTONOMOUS | Only if your application stores the state | Per run; wrap with `scripts/dm_state.py` for multi-session work |

## Environment limitations

- The API keeps no project state for you unless you use its conversation features; the framework's state files live wherever your application puts them.
- Without tools nothing can be verified, and the framework makes the model say so.
- A long system prompt is paid for on every request. Use the compact tier for high-volume, low-risk calls, and measure before assuming the larger tier pays for itself.
- The orchestrator sends whole files in each call. Very large workspaces exceed its context budget; point it at a subdirectory or raise `--max-context-bytes` knowingly.

## Sources

- Text generation and `instructions`: <https://developers.openai.com/api/docs/guides/text>
- Responses API reference: <https://developers.openai.com/api/reference/resources/responses/methods/create>
- Chat Completions reference: <https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create>
