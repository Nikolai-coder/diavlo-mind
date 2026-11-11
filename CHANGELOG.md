# Changelog

All notable changes to DIAVLO MIND are recorded here. Versions follow semantic versioning: a change to the ten rules or the loop is a major version, a new or changed procedure is a minor version, wording and fixes are patches. Changes to the framework's instructions cite the benchmark evidence that justified them (`workflows/protocols/self-improvement.md`).

## [Unreleased]

## [1.1.0] — 2026-11-11

### Added

- **Windows setup in one file** — `DIAVLO-MIND-Setup.bat`, attached to every release. Double-click it on a computer with nothing installed: it looks for Python 3.9 or later and, if there is none, installs Python 3.12 for the current user only (winget when available, otherwise the official python.org installer after checking its MD5 checksum and its Python Software Foundation signature); if it is not inside a DIAVLO MIND folder it downloads the latest release (falling back to the `main` branch) into `%USERPROFILE%\.diavlo-mind\source`; then it runs `scripts/install_all.py` with the options it was given. No administrator rights. Verified: the Windows CI job runs it with `--dry-run` from the repository folder. Not verified on a real machine: the winget and python.org install paths and the download path. `install-all.bat` now points to it when Python is missing.
- **One-step install for every tool** — `install-all.bat` (Windows) and `scripts/install_all.py` detect Claude Code, Codex, Gemini CLI and Antigravity, install the skill in each, and add a short "use `diavlo-mind` on any multi-step task" rule to each tool's global instruction file (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`). The rule sits between marks, files are backed up before they change, a second run changes nothing, and `--uninstall` removes it. Tested against a throwaway home folder; the Windows batch file is exercised by the Windows CI job. Not tested: the four tools obeying the rule. English and Spanish rule text. See `INSTALL.md`.
- `.gitattributes` keeps `*.bat` files exactly as stored (CRLF).

## [1.0.0] — 2026-11-10

First release: the Fable Edition.

### Added

- **Core skill** — `SKILL.md` in Agent Skills format: ten rules, the seven-step loop, four execution modes, evidence levels, delivery format and a routing table for on-demand loading.
- **Execution modes** — FAST, STANDARD, DEEP and AUTONOMOUS PROJECT, with entry conditions, budgets, required artifacts and escalation rules.
- **Twenty procedures** — one per capability, each with trigger, inputs, protocol, tools, outputs, verification and recovery.
- **Eight role agents** — architect, planner, executor, researcher, reviewer, validator, optimizer, orchestrator; valid Claude Code subagents, convertible to Codex and Gemini CLI formats.
- **Protocols** — handoff packets, orchestration, session recovery, Fable Advisor (hybrid) mode with its independent-mode counterpart, and evidence-driven self-improvement.
- **Portable prompts** — micro, compact, standard and full tiers for hosts without Agent Skills, plus ten task templates.
- **Project-state templates and schemas** — nine templates and three JSON schemas.
- **Scripts** (Python 3.9+, standard library only) — mode selector, state manager, packet tools, multi-provider completion client, sequential orchestrator, installer, repository validator, prompt builder, packager, improvement log, GitHub publisher.
- **Adapters** — Claude Code, Claude API, ChatGPT and Codex, OpenAI API, Gemini (API, Gemini CLI, Antigravity) and generic LLM agents, each stating what was and was not verified.
- **Benchmark** — eight tasks with hidden checks and reference solutions, a harness with five runners, scoring, paired comparison with exact sign tests, export of publishable results, and a self-test.
- **Examples** — two recorded live runs and two script walkthroughs.
- **Core-rules lock** — fingerprint of the ten rules, enforced by the validator.
- **Project files** — code of conduct, security policy, citation file, issue and pull-request templates, CI workflow, and a web page in `docs/`.

### Verified in this release

- Repository validation, unit tests, benchmark self-test and packaging pass in CI on Linux, macOS and Windows with Python 3.13, and on Linux with Python 3.9, the oldest version supported (commands in `INSTALL.md`, section 4). The first Python 3.9 run failed 14 of 98 tests: the installer, prompt builder and orchestrator passed `newline=` to `Path.write_text()`, which needs Python 3.10. Fixed before the release.
- The skill, plugin and marketplace manifest load in Claude Code 2.1.322.
- Pilot benchmark, 96 runs on two small models with and without the framework. On the older model the framework arm solved 18 of 24 runs against 14 of 24 (not statistically established, p = 0.22); on the newer model both arms were at the ceiling and the framework cost 28% more. Full results, failures of the framework arm and limits in `evaluation/results/RESULTS.md`.

### Fixed during the release build

- **Orchestrator repair loop tested stale bytecode.** A one-character fix written within the same second as the previous version left Python's cached bytecode in place, so the check ran the old code. The orchestrator now removes the cached bytecode of every Python file it rewrites and runs checks without writing bytecode. Regression test: `BytecodeRegressionTest` in `tests/test_install_and_build.py`.
- **Four benchmark checks were stricter than their task text.** `modules-not-rewritten` (a similarity threshold the reference fix itself passed by only 0.04), `m4-export` (required a final newline the specification does not mention), `design-sections` (letter case of headings) and `design-names-components` (component ids had to appear in kebab case). Each was corrected and the saved workspaces were re-scored for those checks only. One run changed outcome, from failed to solved, in the framework arm; both figures are published in `evaluation/results/RESULTS.md`, and every re-scored run keeps its first outcome in its record.
- **Benchmark checks could alter the work they scored.** A check that ran an agent's own test suite did so inside the saved workspace, so scoring the same work twice could differ. Checks now run on scratch copies; `--rescore --only CHECK_ID` replaces the outcome of named checks and leaves the rest untouched. Covered by `tests/test_benchmark_pipeline.py`.

### Known failures of the framework, open

Four failures observed in the pilot are recorded in `evaluation/improvement/failures.jsonl` and described in the results file: no written handoff across sessions on the older model, test files left in a delivery that had to contain one module, format rules of a specification broken, and no failed run reporting itself incomplete.

### Not verified in this release

- Live calls to the Claude, OpenAI and Gemini APIs (checked against a local mock of the documented formats only).
- Installation in Codex, Gemini CLI, Antigravity, ChatGPT and claude.ai.
- Installing into Claude Code on Windows and macOS (the scripts and tests pass there in CI; the install itself was not tried).
- The stronger reference model of the benchmark (configuration C) and any non-Claude model.
