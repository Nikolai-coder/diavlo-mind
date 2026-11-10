# Adapter: ChatGPT and Codex

Covers the ChatGPT app (Skills, custom GPTs, Projects, custom instructions) and Codex (CLI and IDE extension), which share the Agent Skills format.

**Verification status.** Nothing in this adapter was executed: neither ChatGPT nor Codex was available in the build environment. Paths, commands and limits come from OpenAI's documentation as read on 2026-11-10; items the documentation did not settle are marked *not verified*. The Codex agent files produced by `scripts/install.py` are checked for valid TOML by the test suite, not for loading in Codex.

## Installation

**A. Codex CLI or IDE extension — as a skill.**

```bash
python scripts/install.py codex                      # ~/.agents/skills/diavlo-mind
python scripts/install.py codex --scope project      # <repo>/.agents/skills/diavlo-mind
python scripts/install.py codex --with-agents        # also ~/.codex/agents/dm-*.toml
```

Or by hand: `git clone https://github.com/Nikolai-coder/diavlo-mind ~/.agents/skills/diavlo-mind`. Codex scans `.agents/skills` from the working directory up to the repository root, then `$HOME/.agents/skills`. Restart Codex if the skill does not appear. Invoke it with `$diavlo-mind` or through `/skills`; Codex can also select it from its description.

**B. Codex — as always-on instructions.** Paste `prompts/system/diavlo-mind-compact.md` into `AGENTS.md` (project) or `~/.codex/AGENTS.md` (all projects). Codex stops reading instruction files at 32 KiB combined by default, so use the compact tier.

**C. ChatGPT Skills.** Skills follow the Agent Skills standard and can be built elsewhere and uploaded. Build `dist/diavlo-mind.zip` with `python scripts/package.py` and add it where your workspace manages skills, then select it with `@`. During the beta, skills are off until a workspace owner enables them. *Not verified:* the exact upload dialog and accepted archive layout.

**D. Custom GPT.** Paste `prompts/system/diavlo-mind-compact.md` into the GPT's instructions (kept under 8,000 characters, the limit that field has had; `scripts/build_prompts.py --check` enforces the size) and upload `prompts/system/diavlo-mind-full.md` as a knowledge file.

**E. Project instructions.** Paste the compact tier, or the standard tier if the field accepts it.

**F. Custom instructions.** Paste `prompts/system/diavlo-mind-micro.md` (kept under 1,500 characters for that field).

## Available features

| Feature | ChatGPT (C–F) | Codex (A–B) |
|---|---|---|
| The ten rules, loop and modes | Yes | Yes |
| Progressive disclosure | Skills: yes. GPT, Project and custom instructions: no, the pasted tier is always present | Skill: yes. `AGENTS.md`: no |
| Bundled scripts | Only where a code-execution tool is enabled and the files are present | Yes, in the Codex sandbox |
| Native subagents | No — play the roles in separate passes | Yes, custom agents from TOML files |
| Persistent project state | A file you re-upload, or Project files | `.diavlo-mind/` in the repository |
| Evidence labels and delivery block | Yes | Yes |

## Tool integration

- **ChatGPT.** Use whatever is enabled in the conversation: file uploads, code execution and web search. When a check cannot be executed, the framework requires NOT RUN and the exact command for you to run.
- **Codex.** The shell and file editing of the Codex sandbox cover every procedure. Custom agents inherit the parent session's sandbox and approval settings; an agent file cannot change them, and "do not edit files" in a role prompt is an instruction, not a sandbox.
- `agents/openai.yaml` supplies the display name, short description and default prompt that Codex and ChatGPT show for the skill.

## Model configuration

- **ChatGPT.** The model is chosen in the model picker; the framework has no control over it.
- **Codex.** The session model comes from your Codex configuration. A custom agent file may set `model` and `model_reasoning_effort`. `python scripts/install.py codex --with-agents --executor-model <id>` writes the given model into the executor, researcher, validator and optimizer agents.

## Supported execution modes

| Mode | ChatGPT | Codex |
|---|---|---|
| FAST | Yes | Yes |
| STANDARD | Yes; execution only with a code tool | Yes |
| DEEP | Yes, with roles played in sequence; the review is a cold read, not an independent agent | Yes, with subagents |
| AUTONOMOUS | Limited: you carry the state file between chats | Yes |
| Fable Advisor (hybrid) | No model mixing inside one chat | Different models per agent |

## Environment limitations

- ChatGPT has no project file system shared between chats. Keep `STATE.md` from `memory/templates/` yourself and paste or upload it when resuming.
- In ChatGPT one context plays every role, so author and reviewer share blind spots. The framework tells the model to say that the review was not independent.
- Field limits apply: the compact and micro tiers were sized for them, the standard and full tiers were not.
- Skills in ChatGPT are in beta, depend on workspace settings, and do not sync with Codex.
- Codex: subagent runs use more tokens than a single agent; agent files cannot override sandbox, approval, provider or MCP settings.
- A custom GPT does not load a knowledge file unless retrieval decides to. Critical rules must be in the instructions, which is why the compact tier contains all ten.

## Sources

- Skills in Codex and ChatGPT: <https://learn.chatgpt.com/docs/build-skills>
- Codex subagents: <https://learn.chatgpt.com/docs/agent-configuration/subagents>
- `AGENTS.md`: <https://learn.chatgpt.com/docs/agent-configuration/agents-md>
- Skills in ChatGPT (OpenAI Academy): <https://academy.openai.com/public/clubs/work-users-ynjqu/resources/skills>
