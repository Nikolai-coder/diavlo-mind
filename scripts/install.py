#!/usr/bin/env python3
"""Install DIAVLO MIND as a skill into an agent host.

    python scripts/install.py claude-code                 # ~/.claude/skills/diavlo-mind (skill + 8 agents)
    python scripts/install.py claude-code --scope project # <project>/.claude/skills/diavlo-mind
    python scripts/install.py agents                      # ~/.agents/skills (Codex, Gemini CLI)
    python scripts/install.py codex --with-agents         # + ~/.codex/agents/dm-*.toml
    python scripts/install.py gemini-cli --with-agents    # ~/.gemini/skills + ~/.gemini/agents/dm-*.md
    python scripts/install.py antigravity                 # ~/.gemini/config/skills
    python scripts/install.py custom --dest /path/to/skills
    python scripts/install.py claude-code --uninstall

Options: --dry-run shows what would happen; an existing install is moved to a
timestamped backup unless --force is given. Hybrid setups: --executor-model
and --advisor-model set the model of the installed role agents.

Install locations follow each vendor's documentation as checked in November
2026 (see adapters/). Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "diavlo-mind"

RUNTIME_DIRS = ["agents", "workflows", "prompts", "memory", "adapters"]
RUNTIME_FILES = ["SKILL.md", "README.md", "LICENSE", "VERSION"]
RUNTIME_SCRIPTS = ["dm_state.py", "dm_packet.py", "dm_schema.py", "select_mode.py", "dm_llm.py", "dm_orchestrate.py"]
FULL_EXTRA = ["evaluation", "examples", "tests", "README.es.md", "INSTALL.md", "ARCHITECTURE.md",
              "CHANGELOG.md", "CONTRIBUTING.md"]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "runs", "*.calls")

EXECUTOR_CLASS = {"dm-executor", "dm-researcher", "dm-validator", "dm-optimizer"}
ADVISOR_CLASS = {"dm-architect", "dm-planner", "dm-reviewer", "dm-orchestrator"}
MANIFEST = ".dm-install.json"


def home() -> Path:
    return Path(os.environ.get("DM_HOME") or Path.home())


def destinations(target: str, scope: str, project: Path, dest: Optional[str]) -> Tuple[Path, Optional[Path], str]:
    """Return (skill directory, native agents directory or None, agent format)."""
    user = scope == "user"
    base = home()
    if target == "claude-code":
        root = base / ".claude" if user else project / ".claude"
        return root / "skills" / SKILL_NAME, root / "agents", "claude"
    if target == "agents":
        root = base / ".agents" if user else project / ".agents"
        return root / "skills" / SKILL_NAME, None, ""
    if target == "codex":
        root = base / ".agents" if user else project / ".agents"
        codex_home = Path(os.environ.get("CODEX_HOME") or base / ".codex") if user else project / ".codex"
        return root / "skills" / SKILL_NAME, codex_home / "agents", "codex"
    if target == "gemini-cli":
        root = base / ".gemini" if user else project / ".gemini"
        return root / "skills" / SKILL_NAME, root / "agents", "gemini"
    if target == "antigravity":
        skills = base / ".gemini" / "config" / "skills" if user else project / ".agents" / "skills"
        return skills / SKILL_NAME, None, ""
    if target == "custom":
        if not dest:
            raise SystemExit("error: the custom target needs --dest <skills directory>")
        return Path(dest).expanduser() / SKILL_NAME, None, ""
    raise SystemExit(f"error: unknown target {target}")


def split_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """Flat key: value frontmatter of an agent file, and its body."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta: Dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "#")):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, text[end + 5:].lstrip("\n")


def model_for(agent: str, executor_model: Optional[str], advisor_model: Optional[str]) -> Optional[str]:
    if agent in EXECUTOR_CLASS:
        return executor_model
    if agent in ADVISOR_CLASS:
        return advisor_model
    return None


def set_model(text: str, model: Optional[str]) -> str:
    if not model:
        return text
    return re.sub(r"(?m)^model: .*$", f"model: {model}", text, count=1)


def toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_codex_toml(meta: Dict[str, str], body: str, model: Optional[str]) -> str:
    """Codex custom agent file: name, description, developer_instructions (+ optional model)."""
    lines = [f"name = {toml_string(meta['name'])}", f"description = {toml_string(meta['description'])}"]
    if model and model != "inherit":
        lines.append(f"model = {toml_string(model)}")
    if "'''" not in body:
        lines.append("developer_instructions = '''\n" + body.rstrip("\n") + "\n'''")
    else:
        escaped = body.rstrip("\n").replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        lines.append('developer_instructions = """\n' + escaped + '\n"""')
    return "\n".join(lines) + "\n"


def to_gemini_md(meta: Dict[str, str], body: str, model: Optional[str]) -> str:
    """Gemini CLI subagent file. Claude-specific tool names are dropped so the agent inherits the host's tools."""
    lines = ["---", f"name: {meta['name']}", f"description: {meta['description']}"]
    if model and model != "inherit":
        lines.append(f"model: {model}")
    lines += ["---", "", body.rstrip("\n"), ""]
    return "\n".join(lines)


def agent_files() -> List[Path]:
    return sorted((ROOT / "agents").glob("dm-*.md"))


class Installer:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.project = Path(args.project).resolve()
        self.skill_dir, self.agents_dir, self.agent_format = destinations(args.target, args.scope, self.project, args.dest)
        self.actions: List[str] = []

    def log(self, message: str) -> None:
        self.actions.append(message)
        print(("would " if self.args.dry_run else "") + message)

    def backup_or_remove(self, path: Path) -> None:
        if not path.exists():
            return
        if self.args.force:
            self.log(f"remove existing {path}")
            if not self.args.dry_run:
                shutil.rmtree(path)
            return
        backup = path.with_name(path.name + ".bak-" + datetime.now().strftime("%Y%m%d%H%M%S"))
        self.log(f"move existing install to {backup}")
        if not self.args.dry_run:
            path.rename(backup)

    def copy_payload(self) -> None:
        self.backup_or_remove(self.skill_dir)
        self.log(f"copy skill to {self.skill_dir}")
        if self.args.dry_run:
            return
        self.skill_dir.mkdir(parents=True)
        for name in RUNTIME_FILES:
            if (ROOT / name).is_file():
                shutil.copy2(ROOT / name, self.skill_dir / name)
        for name in RUNTIME_DIRS:
            shutil.copytree(ROOT / name, self.skill_dir / name, ignore=IGNORE)
        (self.skill_dir / "scripts").mkdir()
        for name in RUNTIME_SCRIPTS:
            shutil.copy2(ROOT / "scripts" / name, self.skill_dir / "scripts" / name)
        if self.args.target == "claude-code":
            (self.skill_dir / ".claude-plugin").mkdir()
            shutil.copy2(ROOT / ".claude-plugin" / "plugin.json", self.skill_dir / ".claude-plugin" / "plugin.json")
        if self.args.full:
            for name in FULL_EXTRA:
                source = ROOT / name
                if source.is_dir():
                    shutil.copytree(source, self.skill_dir / name, ignore=IGNORE)
                elif source.is_file():
                    shutil.copy2(source, self.skill_dir / name)

    def apply_models(self) -> None:
        if not (self.args.executor_model or self.args.advisor_model):
            return
        for source in agent_files():
            model = model_for(source.stem, self.args.executor_model, self.args.advisor_model)
            if not model:
                continue
            self.log(f"set {source.stem} model to {model}")
            if not self.args.dry_run:
                target = self.skill_dir / "agents" / source.name
                target.write_text(set_model(target.read_text(encoding="utf-8"), model), encoding="utf-8", newline="\n")

    def native_agents(self) -> List[str]:
        """Write host-native subagent definitions next to the skill. Returns the paths written."""
        if not self.args.with_agents:
            return []
        if not self.agents_dir:
            print(f"note: the {self.args.target} target has no native agent format; role files stay in the skill's agents/ folder")
            return []
        written = []
        for source in agent_files():
            meta, body = split_frontmatter(source.read_text(encoding="utf-8"))
            model = model_for(source.stem, self.args.executor_model, self.args.advisor_model)
            if self.agent_format == "codex":
                target, content = self.agents_dir / f"{source.stem}.toml", to_codex_toml(meta, body, model)
            elif self.agent_format == "gemini":
                target, content = self.agents_dir / source.name, to_gemini_md(meta, body, model)
            else:
                target, content = self.agents_dir / source.name, set_model(source.read_text(encoding="utf-8"), model)
            self.log(f"write agent {target}")
            if not self.args.dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="\n")
            written.append(str(target))
        return written

    def install(self) -> int:
        if not (ROOT / "SKILL.md").is_file():
            raise SystemExit(f"error: {ROOT} does not look like the diavlo-mind folder (no SKILL.md)")
        self.copy_payload()
        self.apply_models()
        agents = self.native_agents()
        if not self.args.dry_run:
            manifest = {
                "skill": SKILL_NAME, "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
                "target": self.args.target, "scope": self.args.scope,
                "installed": datetime.now().isoformat(timespec="seconds"), "agents": agents,
            }
            (self.skill_dir / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print()
        print("Dry run: nothing was written." if self.args.dry_run else f"Installed DIAVLO MIND at {self.skill_dir}")
        print(next_steps(self.args.target, self.skill_dir))
        return 0

    def uninstall(self) -> int:
        manifest_path = self.skill_dir / MANIFEST
        agents: List[str] = []
        if manifest_path.is_file():
            agents = json.loads(manifest_path.read_text(encoding="utf-8")).get("agents", [])
        elif self.agents_dir and self.agent_format:
            suffix = ".toml" if self.agent_format == "codex" else ".md"
            agents = [str(self.agents_dir / (path.stem + suffix)) for path in agent_files()]
        if not self.skill_dir.exists() and not any(Path(a).exists() for a in agents):
            print(f"nothing installed at {self.skill_dir}")
            return 0
        for name in agents:
            path = Path(name)
            if path.is_file():
                self.log(f"remove agent {path}")
                if not self.args.dry_run:
                    path.unlink()
        if self.skill_dir.exists():
            self.log(f"remove {self.skill_dir}")
            if not self.args.dry_run:
                shutil.rmtree(self.skill_dir)
        return 0


def next_steps(target: str, skill_dir: Path) -> str:
    steps = {
        "claude-code": "Next: start a new Claude Code session (or run /reload-plugins), then type /diavlo-mind or just give a task.\n"
                       "Check: `claude plugin list` shows diavlo-mind@skills-dir; the agents appear as diavlo-mind:dm-*.",
        "agents": "Next: restart Codex or Gemini CLI. In Codex type $diavlo-mind or run /skills; in Gemini CLI run /skills list.",
        "codex": "Next: restart Codex, then type $diavlo-mind or run /skills. Agent files, if written, are picked up from the agents folder.",
        "gemini-cli": "Next: run /skills reload (or restart) and /skills list in Gemini CLI.",
        "antigravity": "Next: run /skills reload in Antigravity CLI, or start a new conversation; the skill becomes /diavlo-mind.",
        "custom": "Next: point your agent host at this skills directory and reload it.",
    }
    return steps[target] + f"\nScripts: python \"{skill_dir / 'scripts' / 'dm_state.py'}\" --help"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install DIAVLO MIND into an agent host.")
    parser.add_argument("target", choices=["claude-code", "agents", "codex", "gemini-cli", "antigravity", "custom"])
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--project", default=".", help="project directory for --scope project (default: current directory)")
    parser.add_argument("--dest", help="skills directory for the custom target")
    parser.add_argument("--with-agents", action="store_true", help="also write host-native subagent files")
    parser.add_argument("--executor-model", help="model for executor, researcher, validator and optimizer agents")
    parser.add_argument("--advisor-model", help="model for architect, planner, reviewer and orchestrator agents")
    parser.add_argument("--full", action="store_true", help="also copy evaluation/, examples/, tests/ and the docs")
    parser.add_argument("--force", action="store_true", help="replace an existing install without keeping a backup")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    return parser


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    args = build_parser().parse_args(argv)
    installer = Installer(args)
    return installer.uninstall() if args.uninstall else installer.install()


if __name__ == "__main__":
    sys.exit(main())
