#!/usr/bin/env python3
"""Validate the whole DIAVLO MIND repository.

Checks structure, the Agent Skills format of SKILL.md, agent and procedure
files, internal references, JSON/YAML syntax, prompt sync, version
consistency, the protected core rules, benchmark task layout, Python syntax
and Windows-safe file names.

    python scripts/validate.py              # human-readable report, exit 1 on any error
    python scripts/validate.py --json       # machine-readable
    python scripts/validate.py --release    # also fail on unreplaced __GITHUB_OWNER__ tokens

Python 3.9+, standard library only (PyYAML is used for stricter YAML checks when installed).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import py_compile
import re
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_prompts  # noqa: E402

try:  # optional
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

REQUIRED_FILES = ["SKILL.md", "README.md", "INSTALL.md", "ARCHITECTURE.md", "CHANGELOG.md", "LICENSE", "VERSION"]
REQUIRED_DIRS = ["prompts", "agents", "workflows", "adapters", "memory", "evaluation", "scripts", "examples"]
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
AGENT_FIELDS = {"name", "description", "model", "effort", "maxTurns", "tools", "disallowedTools", "skills",
                "memory", "background", "omitClaudeMd", "isolation", "color"}
ROLES = ["architect", "planner", "executor", "researcher", "reviewer", "validator", "optimizer", "orchestrator"]
PROCEDURE_SECTIONS = ["Trigger", "Inputs", "Protocol", "Tools", "Outputs", "Verification", "Recovery"]
AGENT_SECTIONS = ["You receive", "You do", "You return", "Boundaries", "Rules that always apply"]
ADAPTERS = ["claude-code.md", "claude-api.md", "chatgpt.md", "openai-api.md", "gemini.md", "generic-llm.md"]
ADAPTER_SECTIONS = ["Installation", "Available features", "Tool integration", "Model configuration",
                    "Supported execution modes", "Environment limitations"]
CATEGORIES = ["programming", "debugging", "architecture", "research", "creative", "long-term-project",
              "multi-agent", "error-recovery"]
TOP_LEVEL = ("agents/", "workflows/", "prompts/", "adapters/", "memory/", "evaluation/", "scripts/", "examples/",
             "tests/", "assets/", ".claude-plugin/", ".github/")
OPTIONAL_PATHS = {"evaluation/runs/"}
SKIP_DIRS = {".git", "__pycache__", "dist", "runs", ".pytest_cache", "node_modules", ".diavlo-mind"}
OWNER_TOKEN = "__GITHUB_OWNER__"
PLACEHOLDER_RE = re.compile(r"(?im)^\s*(?:[-*]\s*)?(?:todo|tbd|fixme)\s*[:\-]|lorem ipsum|coming soon|to be written")
WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


class Report:
    def __init__(self) -> None:
        self.sections: List[Tuple[str, List[str], List[str], str]] = []

    def add(self, name: str, errors: List[str], warnings: Optional[List[str]] = None, detail: str = "") -> None:
        self.sections.append((name, errors, warnings or [], detail))

    @property
    def error_count(self) -> int:
        return sum(len(errors) for _, errors, _, _ in self.sections)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def all_files() -> List[Path]:
    out = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in relative.parts) or not path.is_file():
            continue
        out.append(path)
    return out


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def parse_frontmatter(text: str) -> Tuple[Optional[dict], str, str]:
    """Return (metadata, body, error). Understands flat keys and one nested map."""
    if not text.startswith("---\n"):
        return None, text, "file does not start with '---' on its first line"
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text, "frontmatter is not closed with '---'"
    raw, body = text[4:end], text[end + 5:]
    if yaml is not None:
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            return None, body, f"frontmatter is not valid YAML: {exc}"
        if not isinstance(data, dict):
            return None, body, "frontmatter is not a mapping"
        return data, body, ""
    data: dict = {}
    current: Optional[str] = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        nested = line.startswith("  ")
        if ":" not in line:
            return None, body, f"cannot parse frontmatter line: {line!r}"
        key, value = line.strip().split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if nested and current:
            data[current][key.strip()] = value
        elif value == "":
            current = key.strip()
            data[current] = {}
        else:
            current = None
            data[key.strip()] = value
    return data, body, ""


def headings(text: str, level: int = 2) -> List[str]:
    prefix = "#" * level + " "
    return [line[len(prefix):].strip() for line in text.splitlines() if line.startswith(prefix)]


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check_structure() -> Tuple[List[str], List[str], str]:
    errors = [f"missing required file: {name}" for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    errors += [f"missing required directory: {name}/" for name in REQUIRED_DIRS if not (ROOT / name).is_dir()]
    for name in REQUIRED_DIRS:
        folder = ROOT / name
        if folder.is_dir() and not any(p.is_file() for p in folder.rglob("*")):
            errors.append(f"directory is empty: {name}/")
    return errors, [], f"{len(REQUIRED_FILES)} files, {len(REQUIRED_DIRS)} directories"


def check_skill() -> Tuple[List[str], List[str], str]:
    errors, warnings = [], []
    text = read(ROOT / "SKILL.md")
    meta, body, problem = parse_frontmatter(text)
    if meta is None:
        return [problem], [], ""
    for key in meta:
        if key not in SPEC_FIELDS:
            errors.append(f"frontmatter field '{key}' is not in the Agent Skills specification "
                          "(claude.ai uploads and the Skills API reject unknown fields)")
    name = str(meta.get("name", ""))
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        errors.append("name must be 1-64 characters: lowercase letters, digits and single hyphens")
    if any(word in name for word in ("anthropic", "claude")):
        errors.append("name must not contain the reserved words 'anthropic' or 'claude'")
    if ROOT.name != name:
        warnings.append(f"folder is named '{ROOT.name}' but the skill is '{name}': install it into a folder "
                        f"called '{name}' (scripts/install.py does this)")
    description = str(meta.get("description", ""))
    if not 1 <= len(description) <= 1024:
        errors.append(f"description must be 1-1024 characters, is {len(description)}")
    if "<" in description or ">" in description:
        errors.append("description must not contain angle brackets")
    if "use when" not in description.lower():
        errors.append("description should say when to use the skill ('Use when ...')")
    if len(str(meta.get("compatibility", ""))) > 500:
        errors.append("compatibility must be at most 500 characters")
    metadata = meta.get("metadata", {})
    if not isinstance(metadata, dict) or any(not isinstance(v, str) for v in metadata.values()):
        errors.append("metadata must map string keys to string values (quote numbers)")
    lines = text.count("\n") + 1
    tokens = len(body) // 3  # deliberately pessimistic estimate
    if lines > 500:
        errors.append(f"SKILL.md has {lines} lines; the specification recommends under 500")
    if tokens > 5000:
        errors.append(f"SKILL.md body is about {tokens} tokens; keep it under 5000 so it survives compaction whole")
    if "<!-- dm:core-rules:start -->" not in body or body.find("<!-- dm:core-rules:start -->") > 1500:
        errors.append("the core rules must appear near the top of SKILL.md")
    return errors, warnings, f"name={name}, description {len(description)} chars, {lines} lines, ~{tokens} tokens (pessimistic)"


def check_agents() -> Tuple[List[str], List[str], str]:
    errors = []
    folder = ROOT / "agents"
    expected = {f"dm-{role}.md" for role in ROLES}
    present = {p.name for p in folder.glob("*.md")}
    for name in sorted(expected - present):
        errors.append(f"missing agent file: agents/{name}")
    for name in sorted(present - expected):
        errors.append(f"unexpected Markdown file agents/{name}: every .md here is loaded as an agent by plugin hosts")
    for name in sorted(expected & present):
        text = read(folder / name)
        meta, body, problem = parse_frontmatter(text)
        if meta is None:
            errors.append(f"agents/{name}: {problem}")
            continue
        if meta.get("name") != name[:-3]:
            errors.append(f"agents/{name}: name must be '{name[:-3]}'")
        if len(str(meta.get("description", ""))) < 40:
            errors.append(f"agents/{name}: description too short to guide delegation")
        for key in meta:
            if key not in AGENT_FIELDS:
                errors.append(f"agents/{name}: unsupported frontmatter field '{key}'")
        found = headings(body)
        for section in AGENT_SECTIONS:
            if section not in found:
                errors.append(f"agents/{name}: missing section '## {section}'")
        if not any(h in found for h in ("Escalate when", "Stop and report when")):
            errors.append(f"agents/{name}: missing an escalation section")
        if "RESULT PACKET" not in body and "Result:" not in body:
            errors.append(f"agents/{name}: does not define what it returns")
    return errors, [], f"{len(expected & present)} of {len(expected)} role agents"


def check_procedures() -> Tuple[List[str], List[str], str]:
    errors = []
    skill = read(ROOT / "SKILL.md")
    files = sorted((ROOT / "workflows" / "procedures").glob("p*.md"))
    numbers = [p.name[:3] for p in files]
    for number in (f"p{i:02d}" for i in range(1, 21)):
        if numbers.count(number) != 1:
            errors.append(f"expected exactly one procedure file starting with {number}-")
    for path in files:
        found = headings(read(path))
        for section in PROCEDURE_SECTIONS:
            if section not in found:
                errors.append(f"{rel(path)}: missing section '## {section}'")
        if rel(path) not in skill:
            errors.append(f"{rel(path)}: not listed in SKILL.md, so no agent will ever load it")
    for mode in ("fast", "standard", "deep", "autonomous"):
        path = f"workflows/modes/{mode}.md"
        if not (ROOT / path).is_file():
            errors.append(f"missing mode file: {path}")
        elif path not in skill:
            errors.append(f"{path}: not referenced from SKILL.md")
    for protocol in sorted((ROOT / "workflows" / "protocols").glob("*.md")):
        if rel(protocol) not in skill:
            errors.append(f"{rel(protocol)}: not referenced from SKILL.md")
    return errors, [], f"{len(files)} procedures with {len(PROCEDURE_SECTIONS)} sections each, 4 modes"


def check_adapters() -> Tuple[List[str], List[str], str]:
    errors = []
    for name in ADAPTERS:
        path = ROOT / "adapters" / name
        if not path.is_file():
            errors.append(f"missing adapter: adapters/{name}")
            continue
        found = headings(read(path))
        for section in ADAPTER_SECTIONS:
            if section not in found:
                errors.append(f"adapters/{name}: missing section '## {section}'")
    return errors, [], f"{len(ADAPTERS)} adapters with {len(ADAPTER_SECTIONS)} sections each"


LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
CODE_RE = re.compile(r"`([^`\n]+)`")


def check_references() -> Tuple[List[str], List[str], str]:
    errors, checked = [], 0
    for path in all_files():
        if path.suffix != ".md":
            continue
        relative = rel(path)
        local_only = relative.startswith(("evaluation/tasks/", "examples/")) or relative == "prompts/system/diavlo-mind-full.md"
        text = read(path)
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            checked += 1
            if not (path.parent / target).exists() and not (ROOT / target).exists():
                errors.append(f"{relative}: broken link to {target}")
        if local_only:
            continue
        for snippet in CODE_RE.findall(text):
            for token in snippet.split():
                # Trailing punctuation belongs to the sentence; a leading dot belongs to the path (.github/, .agents/).
                token = token.strip(",;:()\"'").rstrip(".")
                if not token.startswith(TOP_LEVEL) or "<" in token or token in OPTIONAL_PATHS:
                    continue
                checked += 1
                if "*" in token:
                    if not list(ROOT.glob(token)):
                        errors.append(f"{relative}: no file matches `{token}`")
                elif not (ROOT / token).exists():
                    errors.append(f"{relative}: referenced path does not exist: `{token}`")
    return errors, [], f"{checked} references"


def check_data_files() -> Tuple[List[str], List[str], str]:
    errors, warnings, count = [], [], 0
    for path in all_files():
        if path.suffix == ".json":
            count += 1
            try:
                json.loads(read(path))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                errors.append(f"{rel(path)}: invalid JSON ({exc})")
        elif path.suffix in (".yml", ".yaml"):
            count += 1
            if yaml is None:
                continue
            try:
                yaml.safe_load(read(path))
            except yaml.YAMLError as exc:
                errors.append(f"{rel(path)}: invalid YAML ({exc})")
    if yaml is None:
        warnings.append("PyYAML not installed: YAML files were not parsed")
    for name in ("task-packet.schema.json", "result-packet.schema.json", "state.schema.json"):
        path = ROOT / "memory" / "schemas" / name
        if not path.is_file():
            errors.append(f"missing schema: memory/schemas/{name}")
    return errors, warnings, f"{count} JSON/YAML files"


def check_prompts() -> Tuple[List[str], List[str], str]:
    errors = []
    contents = build_prompts.desired()
    for path, text in contents.items():
        if not path.is_file() or read(path) != text:
            errors.append(f"{rel(path)} is out of date: run python scripts/build_prompts.py")
    errors += build_prompts.size_problems(contents)
    micro = read(ROOT / "prompts" / "system" / "diavlo-mind-micro.md")
    if len(re.findall(r"(?m)^\d+\. ", micro)) != 10:
        errors.append("prompts/system/diavlo-mind-micro.md must contain the ten rules as a numbered list")
    sizes = ", ".join(f"{p.name.replace('diavlo-mind-', '').replace('.md', '')} {len(t.strip())}"
                      for p, t in sorted(contents.items()) if p.parent.name == "system")
    return errors, [], f"characters: {sizes}"


def check_versions() -> Tuple[List[str], List[str], str]:
    errors = []
    version = build_prompts.version()
    meta, _, _ = parse_frontmatter(read(ROOT / "SKILL.md"))
    if not meta or str(meta.get("metadata", {}).get("version")) != version:
        errors.append(f"SKILL.md metadata.version does not match VERSION ({version})")
    plugin = json.loads(read(ROOT / ".claude-plugin" / "plugin.json"))
    if plugin.get("version") != version:
        errors.append(f".claude-plugin/plugin.json version does not match VERSION ({version})")
    if plugin.get("name") != "diavlo-mind":
        errors.append(".claude-plugin/plugin.json name must be diavlo-mind")
    marketplace = json.loads(read(ROOT / ".claude-plugin" / "marketplace.json"))
    if [p.get("name") for p in marketplace.get("plugins", [])] != ["diavlo-mind"]:
        errors.append(".claude-plugin/marketplace.json must list exactly the diavlo-mind plugin")
    changelog = read(ROOT / "CHANGELOG.md") if (ROOT / "CHANGELOG.md").is_file() else ""
    if f"## [{version}]" not in changelog:
        errors.append(f"CHANGELOG.md has no entry for {version}")
    return errors, [], f"version {version}"


def core_rules_hash() -> str:
    block = build_prompts.core_rules().strip().replace("\r\n", "\n")
    return hashlib.sha256(block.encode("utf-8")).hexdigest()


def check_core_lock() -> Tuple[List[str], List[str], str]:
    path = ROOT / "evaluation" / "improvement" / "core-rules.lock.json"
    if not path.is_file():
        return ["missing evaluation/improvement/core-rules.lock.json"], [], ""
    lock = json.loads(read(path))
    actual = core_rules_hash()
    if lock.get("sha256") != actual:
        return ["the ten core rules changed without a recorded approval - run: "
                "python scripts/dm_improve.py approve-core-change --reason \"<evidence and decision>\""], [], ""
    return [], [], f"sha256 {actual[:12]}… approved {lock.get('approved')}"


def check_python() -> Tuple[List[str], List[str], str]:
    errors, count = [], 0
    with tempfile.TemporaryDirectory() as scratch:
        for path in all_files():
            if path.suffix != ".py":
                continue
            count += 1
            try:
                py_compile.compile(str(path), cfile=str(Path(scratch) / f"{count}.pyc"), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f"{rel(path)}: {exc.msg.strip().splitlines()[-1]}")
    return errors, [], f"{count} Python files compile"


def check_content() -> Tuple[List[str], List[str], str]:
    errors, count = [], 0
    for path in all_files():
        relative = rel(path)
        size = path.stat().st_size
        if size == 0 and path.name != "__init__.py":  # an empty package marker is legitimate
            errors.append(f"{relative}: empty file")
        if size > 1_000_000 and not relative.startswith(("assets/", "evaluation/results/")):
            errors.append(f"{relative}: larger than 1 MB")
        if path.suffix != ".md":
            continue
        count += 1
        text = read(path)
        if len(text.strip()) < 200 and not relative.startswith(("evaluation/tasks/", "examples/")):
            errors.append(f"{relative}: too short to be useful ({len(text.strip())} characters)")
        if not relative.startswith(("evaluation/tasks/", "evaluation/results/", "examples/")):
            match = PLACEHOLDER_RE.search(text)
            if match:
                errors.append(f"{relative}: placeholder text: {match.group(0).strip()!r}")
    return errors, [], f"{count} Markdown files"


def check_tasks() -> Tuple[List[str], List[str], str]:
    errors = []
    folder = ROOT / "evaluation" / "tasks"
    seen: Dict[str, str] = {}
    tasks = sorted(p for p in folder.iterdir() if p.is_dir()) if folder.is_dir() else []
    for task in tasks:
        config = task / "task.json"
        if not config.is_file():
            errors.append(f"{rel(task)}: missing task.json")
            continue
        try:
            data = json.loads(read(config))
        except json.JSONDecodeError:
            continue  # reported by the data-file check
        if data.get("id") != task.name:
            errors.append(f"{rel(config)}: id must equal the folder name")
        if data.get("category") not in CATEGORIES:
            errors.append(f"{rel(config)}: category must be one of {', '.join(CATEGORIES)}")
        seen[str(data.get("category"))] = task.name
        if not data.get("requirements"):
            errors.append(f"{rel(config)}: no requirements listed")
        for stage in data.get("stages", []):
            prompt = stage.get("prompt")
            if prompt and not (task / prompt).is_file():
                errors.append(f"{rel(config)}: stage prompt {prompt} not found")
        if not data.get("stages"):
            errors.append(f"{rel(config)}: no stages")
        if not (task / "checks" / "check.py").is_file():
            errors.append(f"{rel(task)}: missing checks/check.py")
        if not (task / "reference").is_dir():
            errors.append(f"{rel(task)}: missing reference/ solution used to self-test the checks")
    for category in CATEGORIES:
        if category not in seen:
            errors.append(f"no benchmark task covers the category '{category}'")
    return errors, [], f"{len(tasks)} tasks covering {len(seen)} of {len(CATEGORIES)} categories"


def check_filenames() -> Tuple[List[str], List[str], str]:
    errors = []
    lowered: Dict[str, str] = {}
    for path in all_files():
        relative = rel(path)
        for part in path.relative_to(ROOT).parts:
            if re.search(r'[<>:"|?*\\]', part) or part.endswith((" ", ".")):
                errors.append(f"{relative}: name is not valid on Windows")
            if part.split(".")[0].lower() in WINDOWS_RESERVED:
                errors.append(f"{relative}: '{part}' is a reserved name on Windows")
        if len(relative) > 180:
            errors.append(f"{relative}: path longer than 180 characters")
        key = relative.lower()
        if key in lowered:
            errors.append(f"{relative}: collides with {lowered[key]} on case-insensitive file systems")
        lowered[key] = relative
    return errors, [], f"{len(lowered)} files"


def check_owner_token(release: bool) -> Tuple[List[str], List[str], str]:
    hits = []
    for path in all_files():
        if path.suffix in (".png", ".zip") or rel(path) in ("scripts/validate.py", "scripts/publish_github.py"):
            continue
        try:
            if OWNER_TOKEN in read(path):
                hits.append(rel(path))
        except UnicodeDecodeError:
            continue
    if not hits:
        return [], [], "no placeholder tokens"
    message = (f"{OWNER_TOKEN} still present in {len(hits)} file(s): replace it with the GitHub account name "
               "(scripts/publish_github.py does this)")
    return ([message] if release else []), ([] if release else [message]), ", ".join(hits[:4])


def run(release: bool) -> Report:
    report = Report()
    checks: List[Tuple[str, Callable[[], Tuple[List[str], List[str], str]]]] = [
        ("Directory structure", check_structure),
        ("SKILL.md (Agent Skills format)", check_skill),
        ("Agent definitions", check_agents),
        ("Procedures, modes, protocols", check_procedures),
        ("Adapters", check_adapters),
        ("Internal references", check_references),
        ("JSON and YAML", check_data_files),
        ("Prompt tiers in sync", check_prompts),
        ("Version consistency", check_versions),
        ("Core rules lock", check_core_lock),
        ("Python syntax", check_python),
        ("Content (no empty or placeholder files)", check_content),
        ("Benchmark tasks", check_tasks),
        ("File names (Windows-safe)", check_filenames),
        ("Repository placeholders", lambda: check_owner_token(release)),
    ]
    for name, func in checks:
        try:
            errors, warnings, detail = func()
        except Exception as exc:  # a crashing check is itself a failure
            errors, warnings, detail = [f"check crashed: {type(exc).__name__}: {exc}"], [], ""
        report.add(name, errors, warnings, detail)
    return report


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Validate the DIAVLO MIND repository.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--release", action="store_true", help="fail on unreplaced placeholder tokens")
    args = parser.parse_args(argv)
    report = run(args.release)

    if args.json:
        print(json.dumps({
            "ok": report.error_count == 0,
            "errors": report.error_count,
            "checks": [{"name": n, "ok": not e, "errors": e, "warnings": w, "detail": d} for n, e, w, d in report.sections],
        }, indent=2))
        return 0 if report.error_count == 0 else 1

    for name, errors, warnings, detail in report.sections:
        mark = "PASS" if not errors else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
        for line in errors:
            print(f"       error: {line}")
        for line in warnings:
            print(f"       warning: {line}")
    passed = sum(1 for _, errors, _, _ in report.sections if not errors)
    print(f"\n{passed} of {len(report.sections)} checks passed, {report.error_count} error(s).")
    return 0 if report.error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
