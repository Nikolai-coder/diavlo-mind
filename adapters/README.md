# Adapters

The core of DIAVLO MIND is provider-independent text: `SKILL.md`, the procedures, the agent roles and the protocols. An adapter explains how that core reaches a model in one environment, what works there and what does not.

| Environment | Adapter | Install in one line | Native subagents | Scripts run | Status |
|---|---|---|---|---|---|
| Claude Code | [claude-code.md](claude-code.md) | `python scripts/install.py claude-code` | Yes | Yes | Executed on 2026-11-10 |
| Claude API | [claude-api.md](claude-api.md) | system prompt, uploaded skill, or `scripts/dm_orchestrate.py` | Through the orchestrator | In the container or on your machine | Request shape checked against docs and a mock; live API not called |
| ChatGPT and Codex | [chatgpt.md](chatgpt.md) | `python scripts/install.py codex` · paste a prompt tier | Codex: yes · ChatGPT: no | Codex: yes | From documentation; not executed |
| OpenAI API | [openai-api.md](openai-api.md) | `instructions` or `scripts/dm_orchestrate.py` | Through the orchestrator | On your machine | Request shape checked against docs and a mock; live API not called |
| Gemini API, Gemini CLI, Antigravity | [gemini.md](gemini.md) | `python scripts/install.py gemini-cli` or `antigravity` | Gemini CLI: yes | CLIs: yes | From documentation; not executed |
| Anything else | [generic-llm.md](generic-llm.md) | paste a prompt tier, or `scripts/dm_orchestrate.py` | Through the orchestrator | On your machine | `claude-cli`, `cmd` and `compatible` providers tested; no third-party server run |

Every adapter has the same six sections: Installation, Available features, Tool integration, Model configuration, Supported execution modes, Environment limitations.

## What degrades without subagents or files

| Missing capability | Replacement | What is lost |
|---|---|---|
| Subagents | Play the roles in separate passes, or use `scripts/dm_orchestrate.py` | Parallelism; with a single context, the reviewer's independence |
| File system | The orchestrator's file-marker protocol, or state pasted by the user | Progressive disclosure; automatic persistence |
| Shell | The user runs the commands the model names | Verification inside the session: results are NOT RUN until the user reports them |
| Agent Skills support | A prompt tier from `prompts/system/` | Loading detail on demand; the tier is always in context |

## Adding an adapter

Copy the six-section structure, state the verification status at the top, link primary sources, and run `python scripts/validate.py`. Describe only what you executed or read in the vendor's documentation, and say which is which.
