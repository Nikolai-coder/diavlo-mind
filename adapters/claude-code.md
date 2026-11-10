# Adapter: Claude Code

Claude Code is the reference host: it has Agent Skills, native subagents, a shell and a file system, so every part of DIAVLO MIND works here.

**Verification status.** Installation paths A, C and D and the lean installer were executed with Claude Code 2.1.322 on Linux on 2026-11-10 (`claude plugin validate`, `claude plugin list`, `claude plugin details`). The released tree was then installed with the lean installer and invoked as `/diavlo-mind` on a small live edit: 6 turns, a result with its one-line check, confirmed by a separate test. Windows and macOS were not tested; the commands below follow the documentation.

## Installation

Pick one.

**A. Clone into your skills folder** — skill and the eight agents, in every project.

```bash
git clone https://github.com/Nikolai-coder/diavlo-mind ~/.claude/skills/diavlo-mind
```

```powershell
git clone https://github.com/Nikolai-coder/diavlo-mind "$env:USERPROFILE\.claude\skills\diavlo-mind"
```

The folder contains `.claude-plugin/plugin.json`, so Claude Code loads it as a skills-directory plugin named `diavlo-mind@skills-dir`. The skill is invoked as `/diavlo-mind`; the agents appear as `diavlo-mind:dm-architect`, `diavlo-mind:dm-reviewer` and so on. Update with `git pull`.

**B. Lean install with the script** — copies only what the skill needs at run time (no benchmark, no tests).

```bash
python scripts/install.py claude-code                    # ~/.claude/skills/diavlo-mind
python scripts/install.py claude-code --scope project    # <project>/.claude/skills/diavlo-mind, commit it to share with a team
python scripts/install.py claude-code --uninstall
```

An existing install is moved to a timestamped backup unless `--force` is given. `--dry-run` shows what would happen.

**C. As a marketplace plugin.**

```bash
claude plugin marketplace add Nikolai-coder/diavlo-mind
claude plugin install diavlo-mind@diavlo
```

Installed this way the skill is `/diavlo-mind:diavlo-mind`.

**D. For one session, without installing.**

```bash
claude --plugin-dir /path/to/diavlo-mind
```

**Check the installation.**

```bash
claude plugin list                    # shows diavlo-mind with "Status: loaded"
claude plugin details diavlo-mind     # component inventory: 8 agents (and the skill for C and D)
claude plugin validate ~/.claude/skills/diavlo-mind
```

In a running session, `/reload-plugins` picks up a new install.

## Available features

| Feature | Supported | How |
|---|---|---|
| Automatic activation | Yes | Claude loads the skill when a task matches its description |
| Manual activation | Yes | `/diavlo-mind` (or `/diavlo-mind:diavlo-mind` for a marketplace install) |
| Progressive disclosure | Yes | `SKILL.md` is loaded on activation; procedures, modes and protocols are read only when their trigger applies |
| Native subagents | Yes | The eight role files in `agents/` are loaded as plugin agents |
| Bundled scripts | Yes | Run through the Bash tool; needs Python 3.9+ |
| Persistent project state | Yes | `.diavlo-mind/` in the project, written by `scripts/dm_state.py` |
| Headless use | Yes | `claude -p "/diavlo-mind <task>"`, or `--append-system-prompt` with a file from `prompts/system/` |
| Survives context compaction | Mostly | Claude Code re-attaches the first 5,000 tokens of an invoked skill after compaction; `SKILL.md` is below that, so it is kept whole. Files read on demand are not re-attached: re-read them, or invoke the skill again |

## Tool integration

| Procedure needs | Claude Code tool |
|---|---|
| Find code or text | Grep, Glob |
| Read files | Read |
| Change files | Edit, Write |
| Run commands, tests, the bundled scripts | Bash |
| Current facts | WebSearch, WebFetch |
| Delegate | Agent (subagents) |
| Track steps | The built-in task list |

The role agents restrict their own tools in frontmatter: the reviewer has Read, Grep and Glob only; the validator adds Bash; the executor cannot spawn further agents. To make a rule mechanical — for example running tests after every edit — add a Claude Code hook in your own settings. No hooks ship with this repository.

## Model configuration

- The session model is whatever you select with `/model` or `--model`.
- Every role agent ships with `model: inherit`, so it uses the session's model.
- For the hybrid setup (strong model plans and reviews, small model executes) install with:

  ```bash
  python scripts/install.py claude-code --executor-model haiku --advisor-model inherit
  ```

  This sets the model of the executor, researcher, validator and optimizer agents. The subagent `model` field accepts the aliases and model ids your Claude Code version documents.
- `CLAUDE_CODE_SUBAGENT_MODEL` sets a default for agents that do not name a model.
- To run the orchestrator as the main agent: `claude --agent diavlo-mind:dm-orchestrator`.

## Supported execution modes

| Mode | Support | Notes |
|---|---|---|
| FAST | Full | No overhead beyond the skill text |
| STANDARD | Full | |
| DEEP | Full | Reviewer and validator run as subagents with fresh context |
| AUTONOMOUS | Full | State in `.diavlo-mind/`; resume in a new session with `python scripts/dm_state.py resume` |
| Fable Advisor (hybrid) | Full | Different models per agent; see `workflows/protocols/fable-advisor.md` |

## Environment limitations

- A subagent starts with a fresh context and does not inherit the skill the parent invoked. The role files are self-contained for this reason.
- Plugin agents ignore the `permissionMode`, `hooks` and `mcpServers` frontmatter fields.
- Subagents can spawn their own subagents only down to the depth Claude Code allows (three layers by default, configurable); the executor role is not allowed to delegate at all.
- Personal skills in `~/.claude/skills/` are not loaded in cloud sessions. There, put the skill in the repository (`.claude/skills/diavlo-mind/`) or upload `dist/diavlo-mind.zip` to your claude.ai account.
- The scripts call `python`. On systems where only `python3` exists, use that name.
- The skill adds text to the context: roughly 3,000 tokens when activated, plus about 700 tokens always-on for the eight agent descriptions (Claude Code's own estimate from `claude plugin details`: 711) and the skill's own 842-character description.

## Sources

- Skills: <https://code.claude.com/docs/en/skills.md>
- Subagents: <https://code.claude.com/docs/en/sub-agents.md>
- Plugins and skills-directory plugins: <https://code.claude.com/docs/en/plugins/create.md>, <https://code.claude.com/docs/en/plugins/components.md>
- Marketplaces: <https://code.claude.com/docs/en/plugins/create-marketplace.md>
- Headless mode: <https://code.claude.com/docs/en/headless.md>
- Agent Skills specification: <https://agentskills.io/specification>
