#!/usr/bin/env python3
"""Install DIAVLO MIND in every AI agent tool on this computer and make each one use it by default.

    python scripts/install_all.py                  # the tools found on this computer
    python scripts/install_all.py --dry-run        # show everything, write nothing
    python scripts/install_all.py --all            # all four tools, found or not
    python scripts/install_all.py --hosts claude-code,codex
    python scripts/install_all.py --lang es        # the default-use rule in Spanish
    python scripts/install_all.py --uninstall      # remove the skills and the rule

On Windows, double-click install-all.bat (or run it in a terminal with the same options).

For each tool it does two things, both only inside the current user's home folder:

  1. Installs the skill with scripts/install.py: the same files as `install.py <tool>`.
  2. Adds a short rule ("use diavlo-mind on any multi-step task") to the tool's global instruction
     file, between <!-- BEGIN DIAVLO-MIND --> and <!-- END DIAVLO-MIND --> marks. Nothing outside the
     marks is touched, the file is copied to <name>.bak-<time> before it changes, and running the
     script again only refreshes that block.

Global instruction files, as each vendor documents them (see adapters/):

  Claude Code    ~/.claude/CLAUDE.md
  Codex          ~/.codex/AGENTS.md  (or $CODEX_HOME/AGENTS.md)
  Gemini CLI     ~/.gemini/GEMINI.md
  Antigravity    ~/.gemini/GEMINI.md  (the same file: it is written once)

A rule in an instruction file is an instruction to the model, not a switch: the tool follows it almost
always, not every time. Python 3.9+, standard library only, no network.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import install as dm_install  # noqa: E402

MARK_BEGIN_PREFIX = "<!-- BEGIN DIAVLO-MIND"
MARK_BEGIN = MARK_BEGIN_PREFIX + " (managed by scripts/install_all.py; write outside these marks) -->"
MARK_END = "<!-- END DIAVLO-MIND -->"
BOM = b"\xef\xbb\xbf"


# ---------------------------------------------------------------------------------------------- text

BODY = {
    "en": (
        "## DIAVLO MIND: default working method\n\n"
        "For any task with more than one step (coding, debugging, research, writing, planning, long projects), "
        "load the `diavlo-mind` skill ({how}) before you start, without waiting for me to ask. "
        "Do not load it for one-line answers or small talk. When the work is done, report with evidence: "
        "what you checked, what you ran, and what you did not verify."
    ),
    "es": (
        "## DIAVLO MIND: método de trabajo por defecto\n\n"
        "En cualquier tarea de más de un paso (programar, depurar, investigar, escribir, planificar, proyectos largos), "
        "carga la skill `diavlo-mind` ({how}) antes de empezar, sin esperar a que yo lo pida. "
        "No la cargues para respuestas de una línea ni para charla. Al terminar, informa con evidencia: "
        "qué comprobaste, qué ejecutaste y qué no verificaste."
    ),
}

HOW = {
    "en": {"claude-code": "with the Skill tool, or /diavlo-mind", "codex": "as $diavlo-mind",
           "gemini-cli": "through your skills mechanism", "antigravity": "through your skills mechanism"},
    "es": {"claude-code": "con la herramienta Skill, o /diavlo-mind", "codex": "como $diavlo-mind",
           "gemini-cli": "con tu mecanismo de skills", "antigravity": "con tu mecanismo de skills"},
}

MSG = {
    "en": {
        "scan": "AI tools on this computer:",
        "found": "found ({evidence})",
        "missing": "not found",
        "none": "No AI tool found. Choose with --hosts claude-code,codex,gemini-cli,antigravity or use --all.",
        "unknown_host": "Unknown tool: {name}. Valid: {valid}.",
        "rule_text": "Rule written, between marks, in each instruction file (the part in parentheses changes per tool):",
        "dry": "DRY RUN: nothing is written.",
        "skill_ok": "skill installed at {path}",
        "skill_dry": "skill would be installed at {path}",
        "skill_moved": "an install that was not made by this script was moved out of the skills folder to {path}",
        "skill_removed": "skill removed",
        "skill_fail": "skill NOT installed: {why}",
        "skill_skipped": "skill skipped (--rules-only)",
        "created": "rule: created {path}",
        "added": "rule: added to {path} (backup: {backup})",
        "updated": "rule: refreshed in {path} (backup: {backup})",
        "unchanged": "rule: already up to date in {path}",
        "removed": "rule: removed from {path}",
        "absent": "rule: none in {path}",
        "deleted": "rule: removed, and {path} deleted because nothing else was in it",
        "dry_would": "rule: would be {action} {path}",
        "encoding": "rule NOT written: {path} is not UTF-8 (PowerShell's > writes UTF-16). Convert it to UTF-8 and run again.",
        "damaged": "rule NOT written: {path} has a damaged DIAVLO-MIND mark. Fix or delete that block by hand and run again.",
        "oserror": "rule NOT written: {why}",
        "rule_skipped": "rule skipped (--no-rules)",
        "shared": "(same file as {other})",
        "done_ok": "Done. Open a NEW session in each tool so it reads the rule and the skill.",
        "done_bad": "Finished with problems: read the lines marked NOT above.",
        "undo": "To undo: run the same command with --uninstall. Backups are next to each file (.bak-<time>).",
        "dry_done": "Dry run finished. Run again without --dry-run to apply.",
    },
    "es": {
        "scan": "Herramientas de IA en este equipo:",
        "found": "encontrada ({evidence})",
        "missing": "no encontrada",
        "none": "No encuentro ninguna herramienta de IA. Elige con --hosts claude-code,codex,gemini-cli,antigravity o usa --all.",
        "unknown_host": "Herramienta desconocida: {name}. Válidas: {valid}.",
        "rule_text": "Regla que se escribe, entre marcas, en cada archivo de instrucciones (lo que va entre paréntesis cambia según la herramienta):",
        "dry": "PRUEBA EN SECO: no se escribe nada.",
        "skill_ok": "skill instalada en {path}",
        "skill_dry": "la skill se instalaría en {path}",
        "skill_moved": "una instalación que no era de este script se movió fuera de la carpeta de skills a {path}",
        "skill_removed": "skill quitada",
        "skill_fail": "skill NO instalada: {why}",
        "skill_skipped": "skill omitida (--rules-only)",
        "created": "regla: creado {path}",
        "added": "regla: añadida a {path} (copia: {backup})",
        "updated": "regla: actualizada en {path} (copia: {backup})",
        "unchanged": "regla: ya estaba al día en {path}",
        "removed": "regla: quitada de {path}",
        "absent": "regla: no había ninguna en {path}",
        "deleted": "regla: quitada, y {path} borrado porque no tenía nada más",
        "dry_would": "regla: se {action} {path}",
        "encoding": "regla NO escrita: {path} no está en UTF-8 (el > de PowerShell escribe UTF-16). Conviértelo a UTF-8 y ejecuta otra vez.",
        "damaged": "regla NO escrita: {path} tiene una marca DIAVLO-MIND dañada. Arregla o borra ese bloque a mano y ejecuta otra vez.",
        "oserror": "regla NO escrita: {why}",
        "rule_skipped": "regla omitida (--no-rules)",
        "shared": "(mismo archivo que {other})",
        "done_ok": "Hecho. Abre una sesión NUEVA en cada herramienta para que lea la regla y la skill.",
        "done_bad": "Terminó con problemas: lee las líneas marcadas con NO más arriba.",
        "undo": "Para deshacerlo: el mismo comando con --uninstall. Las copias están junto a cada archivo (.bak-<hora>).",
        "dry_done": "Prueba en seco terminada. Ejecuta otra vez sin --dry-run para aplicar.",
    },
}

ACTION_WORD = {
    "en": {"created": "created:", "added": "added to", "updated": "refreshed in", "unchanged": "left as it is in",
           "removed": "removed from", "absent": "left as it is in", "deleted": "removed from"},
    "es": {"created": "creará", "added": "añadirá a", "updated": "actualizará en", "unchanged": "dejará igual",
           "removed": "quitará de", "absent": "dejará igual", "deleted": "quitará de"},
}


def tr(lang: str, key: str, **values: str) -> str:
    return MSG[lang][key].format(**values)


def detect_lang() -> str:
    """Spanish when the system says so, English otherwise. --lang overrides."""
    for name in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        value = os.environ.get(name, "")
        if value:
            return "es" if value.lower().startswith("es") else "en"
    if os.name == "nt":  # pragma: no cover - needs Windows
        try:
            import ctypes
            return "es" if (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x0A else "en"
        except Exception:
            return "en"
    return "en"


# ------------------------------------------------------------------------------------------- the tools

@dataclass(frozen=True)
class Host:
    key: str
    label: str
    rules: Callable[[], Path]
    evidence: Callable[[], List[str]]
    agents: bool


def _which(*names: str) -> List[str]:
    return [found for found in (shutil.which(name) for name in names) if found]


def _dirs(*paths: Path) -> List[str]:
    return [str(path) for path in paths if path.exists()]


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or dm_install.home() / ".codex")


HOSTS: List[Host] = [
    Host("claude-code", "Claude Code", lambda: dm_install.home() / ".claude" / "CLAUDE.md",
         lambda: _which("claude") + _dirs(dm_install.home() / ".claude"), False),
    Host("codex", "Codex", lambda: codex_home() / "AGENTS.md",
         lambda: _which("codex") + _dirs(codex_home()), True),
    Host("gemini-cli", "Gemini CLI", lambda: dm_install.home() / ".gemini" / "GEMINI.md",
         lambda: _which("gemini") + _dirs(dm_install.home() / ".gemini" / "settings.json"), True),
    Host("antigravity", "Antigravity", lambda: dm_install.home() / ".gemini" / "GEMINI.md",
         lambda: _which("antigravity") + _dirs(dm_install.home() / ".gemini" / "config", dm_install.home() / ".gemini" / "antigravity"), False),
]
HOST_KEYS = [host.key for host in HOSTS]


def choose(args: argparse.Namespace, lang: str) -> List[Host]:
    if args.hosts:
        names = [name.strip() for chunk in args.hosts for name in chunk.split(",") if name.strip()]
        for name in names:
            if name not in HOST_KEYS:
                raise SystemExit(tr(lang, "unknown_host", name=name, valid=", ".join(HOST_KEYS)))
        return [host for host in HOSTS if host.key in names]
    if args.all or args.uninstall:
        return list(HOSTS)
    return [host for host in HOSTS if host.evidence()]


# ------------------------------------------------------------------------------- the rule in a file

def render_block(host: Host, lang: str) -> str:
    return MARK_BEGIN + "\n" + BODY[lang].format(how=HOW[lang][host.key]) + "\n" + MARK_END


class MarkError(ValueError):
    """The DIAVLO-MIND marks in a file are not one BEGIN followed by one END."""


def _span(text: str) -> Optional[Tuple[int, int]]:
    begins, ends = text.count(MARK_BEGIN_PREFIX), text.count(MARK_END)
    if begins == 0 and ends == 0:
        return None
    if begins != 1 or ends != 1:
        raise MarkError("marks")
    start, stop = text.index(MARK_BEGIN_PREFIX), text.index(MARK_END)
    if stop < start:
        raise MarkError("marks")
    return start, stop + len(MARK_END)


def apply_block(text: str, block: str) -> Tuple[str, str]:
    """Return the text with the block added or refreshed, and what happened: added, updated or unchanged."""
    span = _span(text)
    if span is None:
        if not text.strip():
            return block + "\n", "added"
        return text.rstrip("\n") + "\n\n" + block + "\n", "added"
    new = text[:span[0]] + block + text[span[1]:]
    return new, ("unchanged" if new == text else "updated")


def remove_block(text: str) -> Tuple[str, bool]:
    span = _span(text)
    if span is None:
        return text, False
    parts = [part for part in (text[:span[0]].rstrip("\n"), text[span[1]:].strip("\n")) if part]
    return ("\n\n".join(parts) + "\n" if parts else ""), True


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".dm-tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def update_rule(path: Path, block: Optional[str], dry_run: bool) -> Tuple[str, str]:
    """Add or refresh the block (block given) or remove it (block None).

    Returns (status, backup path or ""). Status: created, added, updated, unchanged, removed, absent,
    deleted, encoding, damaged.
    """
    existed = path.is_file()
    raw = path.read_bytes() if existed else b""
    has_bom = raw.startswith(BOM)
    try:
        text = raw[len(BOM):].decode("utf-8") if has_bom else raw.decode("utf-8")
    except UnicodeDecodeError:
        return "encoding", ""
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    try:
        if block is None:
            if not existed:
                return "absent", ""
            new, changed = remove_block(text)
            status = "removed" if changed else "absent"
        else:
            new, status = apply_block(text, block)
            if status == "added" and not existed:
                status = "created"
    except MarkError:
        return "damaged", ""
    if status in ("unchanged", "absent"):
        return status, ""
    backup = ""
    if existed:
        backup = str(path.with_name(f"{path.name}.bak-{stamp()}"))
    if dry_run:
        return status, backup
    if backup:
        shutil.copy2(path, backup)
    if block is None and not new.strip():
        path.unlink()
        return "deleted", backup
    data = new.replace("\n", newline).encode("utf-8")
    write_bytes(path, (BOM + data) if has_bom else data)
    return status, backup


# ------------------------------------------------------------------------------------- the skill step

def run_installer(argv: List[str]) -> Tuple[int, str]:
    """Run install.py in-process, keeping its output so this script can say things in one language."""
    buffer = io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buffer):
            code = dm_install.main(argv)
    except SystemExit as stop:
        code = stop.code if isinstance(stop.code, int) else 1
        if not isinstance(stop.code, int) and stop.code:
            buffer.write(str(stop.code))
    return code, buffer.getvalue().strip()


def install_skill(host: Host, args: argparse.Namespace, lang: str) -> Tuple[bool, List[str]]:
    skill_dir, _, _ = dm_install.destinations(host.key, "user", Path.cwd(), None)
    lines: List[str] = []
    argv = [host.key]
    if skill_dir.exists():
        if (skill_dir / dm_install.MANIFEST).is_file():
            argv.append("--force")          # our own earlier install: replace it in place, leave no .bak folder among the skills
        else:
            moved = dm_install.home() / ".diavlo-mind" / "backups" / f"{host.key}-{stamp()}"
            lines.append(tr(lang, "skill_moved", path=str(moved)))
            if not args.dry_run:
                moved.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(skill_dir), str(moved))
    if host.agents and not args.no_agents:
        argv.append("--with-agents")
    if args.executor_model:
        argv += ["--executor-model", args.executor_model]
    if args.advisor_model:
        argv += ["--advisor-model", args.advisor_model]
    if args.dry_run:
        argv.append("--dry-run")
    code, output = run_installer(argv)
    if code != 0:
        lines.append(tr(lang, "skill_fail", why=output.splitlines()[-1] if output else f"exit {code}"))
        return False, lines
    lines.append(tr(lang, "skill_dry" if args.dry_run else "skill_ok", path=str(skill_dir)))
    if args.dry_run:
        lines += ["    " + line for line in output.splitlines() if line.startswith("would ") and "existing install" not in line]
    return True, lines


def remove_skill(host: Host, args: argparse.Namespace, lang: str) -> Tuple[bool, List[str]]:
    argv = [host.key, "--uninstall"] + (["--dry-run"] if args.dry_run else [])
    code, output = run_installer(argv)
    if code != 0:
        return False, [tr(lang, "skill_fail", why=output.splitlines()[-1] if output else f"exit {code}")]
    last = output.splitlines()[-1] if output else ""
    return True, [last if last.startswith("nothing installed") else tr(lang, "skill_removed")]


# ----------------------------------------------------------------------------------------------- main

def rule_line(status: str, path: Path, backup: str, lang: str, dry_run: bool) -> Tuple[bool, str]:
    ok = status not in ("encoding", "damaged")
    if status in ("encoding", "damaged"):
        return ok, tr(lang, status, path=str(path))
    if dry_run and status in ACTION_WORD[lang]:
        return ok, tr(lang, "dry_would", action=ACTION_WORD[lang][status], path=str(path))
    return ok, tr(lang, status, path=str(path), backup=backup)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install DIAVLO MIND in every AI agent tool on this computer and make each one use it by default.")
    parser.add_argument("--hosts", action="append", metavar="LIST",
                        help="comma-separated: " + ", ".join(HOST_KEYS) + " (default: the ones found on this computer)")
    parser.add_argument("--all", action="store_true", help="all four tools, found or not")
    parser.add_argument("--lang", choices=["en", "es"], help="language of the rule and of the messages (default: the system's)")
    parser.add_argument("--no-rules", action="store_true", help="install the skills only; do not touch instruction files")
    parser.add_argument("--rules-only", action="store_true", help="write the rule only; do not install the skills")
    parser.add_argument("--no-agents", action="store_true", help="do not write the Codex and Gemini CLI role-agent files")
    parser.add_argument("--executor-model", help="model for executor, researcher, validator and optimizer agents")
    parser.add_argument("--advisor-model", help="model for architect, planner, reviewer and orchestrator agents")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen and write nothing")
    parser.add_argument("--uninstall", action="store_true", help="remove the skills and the rule")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    dm_install.utf8_stdio()
    args = build_parser().parse_args(argv)
    if args.no_rules and args.rules_only:
        raise SystemExit("error: --no-rules and --rules-only exclude each other")
    lang = args.lang or detect_lang()
    if not (ROOT / "SKILL.md").is_file():
        raise SystemExit(f"error: {ROOT} does not look like the diavlo-mind folder (no SKILL.md)")

    print(tr(lang, "scan"))
    for host in HOSTS:
        found = host.evidence()
        shown = tr(lang, "found", evidence=found[0]) if found else tr(lang, "missing")
        print(f"  {host.label:<12} {shown}")
    selected = choose(args, lang)
    if not selected:
        print("\n" + tr(lang, "none"))
        return 1
    if args.dry_run:
        print("\n" + tr(lang, "dry"))
    if not args.uninstall and not args.no_rules:
        print("\n" + tr(lang, "rule_text"))
        for line in render_block(selected[0], lang).splitlines():
            print("  | " + line)

    ok_all = True
    seen: Dict[Path, str] = {}
    for host in selected:
        print(f"\n{host.label}")
        if args.uninstall:
            ok, lines = remove_skill(host, args, lang) if not args.rules_only else (True, [tr(lang, "skill_skipped")])
        elif args.rules_only:
            ok, lines = True, [tr(lang, "skill_skipped")]
        else:
            ok, lines = install_skill(host, args, lang)
        ok_all &= ok
        for line in lines:
            print("  " + line)
        if args.no_rules:
            print("  " + tr(lang, "rule_skipped"))
            continue
        path = host.rules()
        if path in seen:
            print("  " + tr(lang, "shared", other=seen[path]))
            continue
        seen[path] = host.label
        try:
            status, backup = update_rule(path, None if args.uninstall else render_block(host, lang), args.dry_run)
        except OSError as problem:
            ok_all = False
            print("  " + tr(lang, "oserror", why=str(problem)))
            continue
        ok, line = rule_line(status, path, backup, lang, args.dry_run)
        ok_all &= ok
        print("  " + line)

    print()
    if args.dry_run:
        print(tr(lang, "dry_done"))
    elif ok_all:
        print(tr(lang, "done_ok"))
    else:
        print(tr(lang, "done_bad"))
    if not args.dry_run and not args.uninstall:
        print(tr(lang, "undo"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
