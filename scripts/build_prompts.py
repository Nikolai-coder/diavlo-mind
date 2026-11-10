#!/usr/bin/env python3
"""Keep the portable prompts and version stamps in sync with their sources.

Single sources of truth:
    VERSION                      -> version in SKILL.md, plugin.json and the prompt tiers
    SKILL.md (core rules block)  -> the same block inside the compact and standard prompts
    all skill files              -> prompts/system/diavlo-mind-full.md (generated bundle)

    python scripts/build_prompts.py           # rewrite whatever is out of date
    python scripts/build_prompts.py --check   # exit 1 if anything is stale or over its size limit

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
SYSTEM_DIR = ROOT / "prompts" / "system"
RULES_RE = re.compile(r"(<!-- dm:core-rules:start -->)(.*?)(<!-- dm:core-rules:end -->)", re.S)
VERSION_RE = re.compile(r"v\d+\.\d+\.\d+")

# Character limits of the places these tiers are meant to be pasted into.
LIMITS = {"diavlo-mind-micro.md": 1500, "diavlo-mind-compact.md": 8000}

BUNDLE_SECTIONS = [
    ("Execution modes", "workflows/modes", "*.md"),
    ("Procedures", "workflows/procedures", "*.md"),
    ("Protocols", "workflows/protocols", "*.md"),
    ("Agent roles", "agents", "dm-*.md"),
    ("Templates", "prompts/templates", "*.md"),
    ("Project-state templates", "memory/templates", "*.md"),
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def version() -> str:
    value = read(ROOT / "VERSION").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise SystemExit(f"error: VERSION must look like 1.2.3, got {value!r}")
    return value


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:].lstrip("\n")
    return text


def core_rules() -> str:
    match = RULES_RE.search(read(ROOT / "SKILL.md"))
    if not match:
        raise SystemExit("error: core rules block not found in SKILL.md")
    return match.group(2)


def with_rules(text: str, rules: str) -> str:
    if not RULES_RE.search(text):
        raise SystemExit("error: a prompt tier is missing the core-rules markers")
    return RULES_RE.sub(lambda m: m.group(1) + rules + m.group(3), text, count=1)


def with_version(text: str, value: str) -> str:
    first, _, rest = text.partition("\n")
    return VERSION_RE.sub(f"v{value}", first, count=1) + "\n" + rest


def build_full(value: str) -> str:
    parts = [
        f"# DIAVLO MIND v{value} — full reference bundle",
        "",
        "GENERATED FILE — do not edit. Rebuild with `python scripts/build_prompts.py`.",
        "",
        "This single document contains the whole framework for models that cannot open files: the core "
        "instructions first, then every file they refer to. Where the instructions say to read a path such as "
        "`workflows/procedures/p07-debugging-recovery.md`, find the section headed `FILE: <that path>` below. "
        "Commands that mention `scripts/` need the repository; without it, keep the same information by hand.",
        "",
        "=" * 78,
        "FILE: SKILL.md",
        "=" * 78,
        "",
        strip_frontmatter(read(ROOT / "SKILL.md")).rstrip(),
    ]
    for title, folder, pattern in BUNDLE_SECTIONS:
        files = sorted((ROOT / folder).glob(pattern))
        if not files:
            raise SystemExit(f"error: no files match {folder}/{pattern}")
        parts += ["", "", "#" * 78, f"# {title.upper()}", "#" * 78]
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            parts += ["", "=" * 78, f"FILE: {relative}", "=" * 78, "", strip_frontmatter(read(path)).rstrip()]
    return "\n".join(parts) + "\n"


def sync_skill_version(text: str, value: str) -> str:
    return re.sub(r'(?m)^(  version: )"[^"]*"', rf'\g<1>"{value}"', text, count=1)


def sync_plugin_version(text: str, value: str) -> str:
    data = json.loads(text)
    data["version"] = value
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def desired() -> Dict[Path, str]:
    """Every managed file with the content it should have."""
    value = version()
    rules = core_rules()
    out: Dict[Path, str] = {}
    out[ROOT / "SKILL.md"] = sync_skill_version(read(ROOT / "SKILL.md"), value)
    plugin = ROOT / ".claude-plugin" / "plugin.json"
    out[plugin] = sync_plugin_version(read(plugin), value)
    out[SYSTEM_DIR / "diavlo-mind-micro.md"] = with_version(read(SYSTEM_DIR / "diavlo-mind-micro.md"), value)
    for name in ("diavlo-mind-compact.md", "diavlo-mind-standard.md"):
        out[SYSTEM_DIR / name] = with_version(with_rules(read(SYSTEM_DIR / name), rules), value)
    out[SYSTEM_DIR / "diavlo-mind-full.md"] = build_full(value)
    return out


def size_problems(contents: Dict[Path, str]) -> List[str]:
    problems = []
    for path, text in contents.items():
        limit = LIMITS.get(path.name)
        if limit and len(text.strip()) > limit:
            problems.append(f"{path.relative_to(ROOT).as_posix()} is {len(text.strip())} characters; the limit is {limit}")
    return problems


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report stale files without writing")
    args = parser.parse_args(argv)

    contents = desired()
    stale = [path for path, text in contents.items() if not path.is_file() or read(path) != text]
    problems = size_problems(contents)

    if args.check:
        for path in stale:
            print(f"stale: {path.relative_to(ROOT).as_posix()} (run scripts/build_prompts.py)")
        for line in problems:
            print(f"too long: {line}")
        if not stale and not problems:
            print(f"prompts are up to date ({len(contents)} managed files, version {version()})")
        return 1 if stale or problems else 0

    for path in stale:
        path.write_text(contents[path], encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT).as_posix()}")
    if not stale:
        print("nothing to do")
    for path, text in sorted(contents.items()):
        if path.parent == SYSTEM_DIR:
            limit = LIMITS.get(path.name)
            note = f" (limit {limit})" if limit else ""
            print(f"  {path.name}: {len(text.strip())} characters{note}")
    for line in problems:
        print(f"error: {line}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
