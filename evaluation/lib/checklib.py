"""Helpers shared by the hidden check scripts in evaluation/tasks/*/checks/.

A check script receives the workspace to inspect and prints one JSON object:

    {"checks": [{"id": "c1", "requirement": "R1", "kind": "functional",
                 "passed": true, "detail": "...", "required": true}]}

Candidate code is never imported into the checker process: it always runs in a
subprocess with a timeout, so a broken or hanging submission cannot take the
checker down with it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

KINDS = ("functional", "requirement", "scope", "process")
IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".DS_Store", ".diavlo-mind", ".git", ".claude"}


class Checks:
    """Collects check results and prints them in the format the harness expects."""

    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []

    def add(self, check_id: str, requirement: str, passed: bool, detail: str = "",
            kind: str = "functional", required: bool = True) -> bool:
        if kind not in KINDS:
            raise ValueError(f"unknown check kind {kind}")
        self.items.append({"id": check_id, "requirement": requirement, "kind": kind,
                           "passed": bool(passed), "detail": str(detail)[:400], "required": required})
        return bool(passed)

    def emit(self) -> None:
        print(json.dumps({"checks": self.items}, indent=2))


def workspace_arg() -> Path:
    if len(sys.argv) < 2:
        raise SystemExit("usage: check.py <workspace-directory>")
    return Path(sys.argv[1]).resolve()


def snapshot_dir(stage_id: str) -> Optional[Path]:
    """Copy of a workspace as it was when the given stage finished (set by the harness)."""
    base = os.environ.get("DM_SNAPSHOTS")
    if not base:
        return None
    path = Path(base).resolve() / stage_id  # absolute: checks run programs from other working directories
    return path if path.is_dir() else None


def run(command: List[str], cwd: Path, timeout: int = 60, stdin: Optional[str] = None,
        env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Run a command. Never raises: failures come back as data."""
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    environment.update(env or {})
    try:
        done = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, input=stdin, env=environment)
        return {"code": done.returncode, "out": done.stdout, "err": done.stderr, "timeout": False}
    except subprocess.TimeoutExpired:
        return {"code": 124, "out": "", "err": f"timed out after {timeout}s", "timeout": True}
    except OSError as exc:
        return {"code": 127, "out": "", "err": str(exc), "timeout": False}


def run_python(cwd: Path, code: str, timeout: int = 60) -> Dict[str, Any]:
    """Run a snippet with the workspace as the current directory and first on the import path."""
    return run([sys.executable, "-c", textwrap.dedent(code)], cwd, timeout)


def run_cases(cwd: Path, setup: str, cases: Dict[str, str], timeout: int = 60) -> Dict[str, Dict[str, Any]]:
    """Evaluate several expressions against candidate code in one subprocess.

    `setup` imports what is needed. Each case is a Python expression. The result
    maps a case name to {"ok": bool, "value": <json value> | "error": "<ExceptionType>: message"}.
    Values that are not JSON-serializable are returned as their repr().
    """
    driver = f"""
import json, sys
results = {{}}
try:
{textwrap.indent(textwrap.dedent(setup).strip() or 'pass', '    ')}
    setup_error = None
except BaseException as exc:
    setup_error = type(exc).__name__ + ": " + str(exc)
cases = json.loads({json.dumps(json.dumps(cases))})
for name, expression in cases.items():
    if setup_error:
        results[name] = {{"ok": False, "error": "setup failed: " + setup_error}}
        continue
    try:
        value = eval(expression)
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            value = repr(value)
        results[name] = {{"ok": True, "value": value}}
    except BaseException as exc:
        results[name] = {{"ok": False, "error": type(exc).__name__ + ": " + str(exc), "type": type(exc).__name__}}
sys.stdout.write("\\n@@RESULTS@@" + json.dumps(results))
"""
    done = run([sys.executable, "-c", driver], cwd, timeout)
    marker = done["out"].rfind("@@RESULTS@@")
    if marker == -1:
        problem = (done["err"] or done["out"] or "no output").strip().splitlines()[-1:] or ["no output"]
        return {name: {"ok": False, "error": f"driver failed: {problem[0][:200]}"} for name in cases}
    return json.loads(done["out"][marker + len("@@RESULTS@@"):])


def raised(result: Dict[str, Any], exception: str) -> bool:
    """True when a run_cases result is the named exception type."""
    return (not result.get("ok")) and result.get("type") == exception


def visible_files(workspace: Path) -> List[str]:
    """Relative paths of files in a workspace, ignoring caches and tool folders."""
    out = []
    for path in sorted(workspace.rglob("*")):
        relative = path.relative_to(workspace)
        if any(part in IGNORED_NAMES for part in relative.parts) or path.suffix == ".pyc":
            continue
        if path.is_file():
            out.append(relative.as_posix())
    return out


def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def read_json(path: Path) -> Any:
    text = read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
