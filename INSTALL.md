# Installation

DIAVLO MIND is a folder. Installing it means putting that folder where your agent looks for skills, or pasting one of its prompt files where your model reads instructions. Nothing is compiled and nothing is downloaded at run time.

**Requirements:** none for the instructions themselves. The optional scripts need Python 3.9 or later and no extra packages.

## 1. Get the files

**Windows, shortest path:** download [`DIAVLO-MIND-Setup.bat`](https://github.com/Nikolai-coder/diavlo-mind/blob/main/DIAVLO-MIND-Setup.bat) (*Download raw file*), or take it from the latest release, and double-click it. It installs Python 3.12 for your user if no Python 3.9+ is found (winget, or the python.org installer after checking its MD5 checksum and signature), downloads the latest release to `%USERPROFILE%\.diavlo-mind\source` and runs the all-tools installer described in section 2, passing on any option you give it. Run from inside a cloned or unpacked folder, it uses that folder and downloads nothing. That is all; the rest of this section is for the other ways.

```bash
git clone https://github.com/Nikolai-coder/diavlo-mind
cd diavlo-mind
```

Or download `DIAVLO-MIND-FABLE-EDITION.zip` from the releases page and unpack it. The archive unpacks to a folder named `DIAVLO-MIND`; the installer below copies it to the correct, lower-case skill folder name for you.

## 2. Install for your environment

### All your AI tools at once

On Windows, double-click `install-all.bat` or run it from a terminal. On macOS and Linux run `python3 scripts/install_all.py`. Same options everywhere:

```bash
install-all.bat --dry-run       # first: show what it would do, write nothing
install-all.bat                 # install in the tools found on this computer
install-all.bat --lang es       # write the rule in Spanish (default: the system language)
install-all.bat --all           # all four tools, found or not
install-all.bat --uninstall     # remove the skills and the rule
```

For each of Claude Code, Codex, Gemini CLI and Antigravity it does two things, only inside your own user folder:

1. Installs the skill and, for Codex and Gemini CLI, the role agents: the same files as `install.py <tool>`.
2. Adds a short rule to the tool's global instruction file, so the tool loads `diavlo-mind` on any task with more than one step without being asked:

| Tool | Instruction file |
|---|---|
| Claude Code | `~/.claude/CLAUDE.md` |
| Codex | `~/.codex/AGENTS.md` (or `$CODEX_HOME/AGENTS.md`) |
| Gemini CLI and Antigravity | `~/.gemini/GEMINI.md` (the same file for both, written once) |

How it treats your files:

- The rule sits between `<!-- BEGIN DIAVLO-MIND -->` and `<!-- END DIAVLO-MIND -->` marks. Nothing outside them is changed; your line endings and UTF-8 byte-order mark are kept.
- Before a file changes it is copied to `<name>.bak-<time>`. Running the script again only refreshes the block and makes no new copy when nothing changed.
- A file that is not UTF-8 (PowerShell's `>` writes UTF-16) or that has a damaged mark is left alone, and the script says so and exits with an error.
- A skill folder that this script did not install is moved to `~/.diavlo-mind/backups/`, not left among your skills. A folder it installed itself is replaced in place.
- `--uninstall` removes the skills, the agent files and the block, and deletes an instruction file only if nothing else is in it.
- Options: `--hosts claude-code,codex` to choose, `--no-rules` (skills only), `--rules-only`, `--no-agents`, `--executor-model` and `--advisor-model` (as in `install.py`).

**What this does and does not guarantee.** A rule in an instruction file is an instruction to the model, not a switch: the tool follows it nearly always, not every time, and each activation adds about 3,000 tokens of context (see `adapters/claude-code.md`). The Gemini CLI and Antigravity paths were checked against their documentation on 2026-11-10. The tests run the script against a throwaway home folder on Linux, macOS and Windows in CI; no test has run the four tools themselves to see them obey the rule.

### Claude Code

```bash
python scripts/install.py claude-code
```

This copies the skill to `~/.claude/skills/diavlo-mind` together with its plugin manifest, so Claude Code loads the skill (`/diavlo-mind`) and the eight role agents (`diavlo-mind:dm-architect`, …). Start a new session, or run `/reload-plugins`.

| Variant | Command |
|---|---|
| Only for one project (commit it to share with your team) | `python scripts/install.py claude-code --scope project --project /path/to/project` |
| Without the script | `git clone https://github.com/Nikolai-coder/diavlo-mind ~/.claude/skills/diavlo-mind` |
| As a marketplace plugin | `claude plugin marketplace add Nikolai-coder/diavlo-mind` then `claude plugin install diavlo-mind@diavlo` |
| For one session only | `claude --plugin-dir /path/to/diavlo-mind` |
| Strong model plans, small model executes | `python scripts/install.py claude-code --executor-model haiku --advisor-model inherit` |

On Windows the personal skills folder is `%USERPROFILE%\.claude\skills\`. The script resolves it for you; for a manual clone use `git clone https://github.com/Nikolai-coder/diavlo-mind "$env:USERPROFILE\.claude\skills\diavlo-mind"` in PowerShell.

Check it:

```bash
claude plugin list                  # diavlo-mind … Status: loaded
claude plugin details diavlo-mind   # lists the 8 agents
```

Then ask for something non-trivial, or type `/diavlo-mind` followed by your task.

### Codex (CLI and IDE extension)

```bash
python scripts/install.py codex                 # skill in ~/.agents/skills/diavlo-mind
python scripts/install.py codex --with-agents   # also the role agents in ~/.codex/agents/
```

Restart Codex, then type `$diavlo-mind` or open `/skills`.

### Gemini CLI

```bash
python scripts/install.py gemini-cli --with-agents   # ~/.gemini/skills/ and ~/.gemini/agents/
```

Then `/skills reload` and `/skills list`.

### Antigravity

```bash
python scripts/install.py antigravity                 # ~/.gemini/config/skills/diavlo-mind
python scripts/install.py antigravity --scope project # <workspace>/.agents/skills/diavlo-mind
```

### claude.ai, ChatGPT and other upload-based hosts

```bash
python scripts/package.py      # writes dist/diavlo-mind.zip
```

Upload `dist/diavlo-mind.zip` where the product manages skills. The archive contains one folder, `diavlo-mind/`, with `SKILL.md` directly inside.

### Any model with one instruction field

Paste one file from `prompts/system/`:

| File | Size | For |
|---|---|---|
| `diavlo-mind-micro.md` | under 1,500 characters | Small "custom instructions" fields |
| `diavlo-mind-compact.md` | under 8,000 characters | Custom GPT instructions, project instructions, small models |
| `diavlo-mind-standard.md` | about 14,000 characters | API system prompts, agents with tools |
| `diavlo-mind-full.md` | about 180,000 characters | Large-context models, or as an attached reference file |

### Any API, without an agent host

```bash
export ANTHROPIC_API_KEY=…        # or OPENAI_API_KEY, GEMINI_API_KEY
python scripts/dm_orchestrate.py --task task.md --workspace ./project --mode standard \
  --executor anthropic:<model-id> --check-cmd "python -m pytest -q"
```

Providers: `anthropic`, `openai`, `openai-responses`, `gemini`, `compatible` (any OpenAI-compatible server), `claude-cli` (your local Claude Code, no API key), `cmd` (any command that reads a prompt on standard input). Details per environment are in `adapters/`.

## 3. Options of the installer

```
python scripts/install.py <target> [options]

targets   claude-code | agents | codex | gemini-cli | antigravity | custom
--scope user|project      where to install (default: user)
--project DIR             project directory for --scope project
--dest DIR                skills directory for the custom target
--with-agents             also write host-native agent files (Codex, Gemini CLI; standalone copies for Claude Code)
--executor-model MODEL    model for the executor, researcher, validator and optimizer agents
--advisor-model MODEL     model for the architect, planner, reviewer and orchestrator agents
--full                    also copy evaluation/, examples/, tests/ and the documentation
--dry-run                 show what would happen
--force                   replace an existing install without keeping a backup
--uninstall               remove the skill and the agent files the installer wrote
```

An existing install is moved to `diavlo-mind.bak-<timestamp>` unless `--force` is given.

## 4. Verify the download

```bash
python scripts/validate.py                 # structure, formats, references, versions, prompt sync
python -m unittest discover -s tests       # unit tests for every script
python evaluation/selftest.py              # the benchmark's checks reject empty work and accept the reference solutions
```

## 5. Update and remove

```bash
git pull && python scripts/install.py claude-code      # update (the old copy is backed up)
python scripts/install.py claude-code --uninstall      # remove
```

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The skill does not appear in Claude Code | Start a new session or run `/reload-plugins`. Check `claude plugin list`. In cloud sessions personal skills are not loaded: install with `--scope project` and commit the folder. |
| A strict validator says the name does not match the folder | The folder must be called `diavlo-mind`. Unpacking the release archive gives `DIAVLO-MIND`; use `scripts/install.py`, or rename the folder. |
| `python` is not found | Use `python3` (Linux, macOS) or `py` (Windows). |
| The agent stops following the skill late in a long session | The context was compacted. Invoke the skill again (`/diavlo-mind`), or let the project state carry the work (`python scripts/dm_state.py resume`). |
| The orchestrator reports "file block(s) were not closed" | The model's reply was cut off. Raise `--max-tokens`, split the task (`--mode deep`), or use a model with a larger output limit. |
| `scripts/validate.py` warns about an owner placeholder | The copy was never published; `scripts/publish_github.py` writes the GitHub account name where the placeholder is. |
