# Adapter: Gemini (API, Gemini CLI, Antigravity)

Covers the Gemini API and Google's two command-line agents, which both read Agent Skills.

**Verification status.** Nothing in this adapter was executed against Google's services or tools: none were available in the build environment. The `generateContent` request shape used by `scripts/dm_llm.py` was checked against the API reference on 2026-11-10 and exercised against a local mock. CLI paths and commands come from the Gemini CLI and Antigravity documentation as read on the same day. The agent files produced by `scripts/install.py gemini-cli --with-agents` are checked by the test suite for their frontmatter, not for loading in Gemini CLI.

Note on the two CLIs: Google's documentation states that Gemini CLI was replaced by Antigravity CLI on 2026-06-18 for unpaid and Google One users. Use the section that matches the tool you have.

## Installation

**A. Gemini API** — put a prompt tier in the system instruction.

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/<model-id>:generateContent" \
  -H "Content-Type: application/json" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -d "$(python3 - <<'EOF'
import json, pathlib
print(json.dumps({
    "system_instruction": {"parts": [{"text": pathlib.Path("prompts/system/diavlo-mind-standard.md").read_text(encoding="utf-8")}]},
    "contents": [{"role": "user", "parts": [{"text": "Your task here"}]}],
}))
EOF
)"
```

The newer Interactions API takes the same text as a plain string in `system_instruction`.

**B. Bundled orchestrator.**

```bash
export GEMINI_API_KEY=…
python scripts/dm_orchestrate.py --task task.md --workspace ./project --mode standard \
  --executor gemini:<model-id> --check-cmd "go test ./..."
```

**C. Gemini CLI — as a skill.**

```bash
python scripts/install.py gemini-cli                  # ~/.gemini/skills/diavlo-mind
python scripts/install.py gemini-cli --with-agents    # also ~/.gemini/agents/dm-*.md
python scripts/install.py gemini-cli --scope project  # <project>/.gemini/skills/diavlo-mind
```

Gemini CLI can also install from Git itself: `gemini skills install https://github.com/Nikolai-coder/diavlo-mind`. Then `/skills reload` and `/skills list`. The CLI asks for consent the first time it activates a skill.

**D. Antigravity (CLI, IDE, app) — as a skill.**

```bash
python scripts/install.py antigravity                   # ~/.gemini/config/skills/diavlo-mind
python scripts/install.py antigravity --scope project   # <workspace>/.agents/skills/diavlo-mind
```

In the CLI run `/skills reload` or start a new conversation; the skill becomes the command `/diavlo-mind`.

**E. A Gem or other custom-instruction field.** Paste `prompts/system/diavlo-mind-compact.md`. *Not verified:* the length that field accepts.

## Available features

| Feature | API (A, B) | Gemini CLI (C) | Antigravity (D) |
|---|---|---|---|
| The ten rules, loop and modes | Yes | Yes | Yes |
| Progressive disclosure | No | Yes | Yes |
| Bundled scripts | B: on your machine | Yes, through the shell tool | Yes |
| Native subagents | No | Yes, from `.gemini/agents/*.md` | Not covered here: role files stay in the skill's `agents/` folder |
| Persistent project state | Your application | `.diavlo-mind/` in the project | `.diavlo-mind/` in the workspace |

## Tool integration

- **API.** Declare tools as `functionDeclarations` (name, description, JSON-schema parameters). Return each result as a `functionResponse` part carrying the `id` of the call. Models that emit thought signatures require them to be sent back unchanged with the function call; the official SDKs do this for you. The bundled orchestrator needs no tools.
- **Gemini CLI.** Its file, search and shell tools cover the procedures. Generated subagent files omit the `tools` field so each agent inherits the session's tools; add a `tools` list by hand to restrict the reviewer and validator to read-only tools.
- **Antigravity.** The agent reads `SKILL.md` when the description matches, then follows it with the tools the product provides.

## Model configuration

- **API.** Any model id your key can use. The documentation notes that recent models ignore `temperature`, `top_p` and `top_k`; the scripts never send them.
- **Gemini CLI.** A subagent file may set `model`, `temperature`, `max_turns` and `timeout_mins`. `--executor-model <id>` at install time writes `model` into the executor-class agents.
- **Antigravity.** Models are chosen inside the product.
- Other endpoints: `DM_GEMINI_BASE_URL`.

## Supported execution modes

| Mode | API with system instruction | API with orchestrator | Gemini CLI | Antigravity |
|---|---|---|---|---|
| FAST | Yes | `--mode fast` | Yes | Yes |
| STANDARD | Yes; NOT RUN without tools | `--mode standard` | Yes | Yes |
| DEEP | Partly: one context for all roles | `--mode deep` | Yes | Yes; the review is a separate pass |
| AUTONOMOUS | Only with your own state storage | Per run | Yes | Yes |

## Environment limitations

- **Gemini CLI subagents cannot call other subagents.** The orchestrator role must be the main agent; installing `dm-orchestrator` as a subagent there gives it nobody to delegate to.
- The API keeps no project state unless you use its stateful features; treat state as your application's job.
- Without tools the model cannot verify, and the framework requires it to say NOT RUN.
- Skill discovery differs by product and version: Gemini CLI reads `~/.gemini/skills/` and `.gemini/skills/` (with `.agents/skills/` as an alias); Antigravity reads `~/.gemini/config/skills/` and `<workspace>/.agents/skills/`. If a skill does not appear, check the product's own skill listing first.

## Sources

- `generateContent` reference: <https://aistudio.google.com/api-reference/generate-content>
- Function calling: <https://aistudio.google.com/docs/function-calling>
- Interactions API: <https://aistudio.google.com/docs/interactions>
- Gemini CLI skills: <https://geminicli.com/docs/cli/skills/>
- Gemini CLI subagents: <https://geminicli.com/docs/core/subagents/>
- Antigravity skills: <https://antigravity.google/docs/skills>
