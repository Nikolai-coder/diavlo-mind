#!/usr/bin/env python3
"""Hidden checks for longterm-notes-cli. Usage: check.py <workspace>

The harness sets DM_SNAPSHOTS so the state after the first session can be
inspected. Without it (manual runs) the final workspace stands in for it.
"""
import ast
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from checklib import Checks, read_text, run, snapshot_dir, workspace_arg  # noqa: E402

WORK = workspace_arg()
FIRST = snapshot_dir("session-1") or WORK
checks = Checks()


class Cli:
    """Runs notes.py from a given project in a fresh, empty working directory."""

    def __init__(self, project: Path):
        self.script = project / "notes.py"
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)

    def __call__(self, *args):
        if not self.script.is_file():
            return {"code": 127, "out": "", "err": "notes.py missing"}
        done = run([sys.executable, str(self.script), *args], self.cwd, timeout=30)
        done["out"] = done["out"].replace("\r\n", "\n")
        done["err"] = done["err"].replace("\r\n", "\n")
        return done

    def ok(self, *args):
        done = self(*args)
        return done["out"] if done["code"] == 0 else f"<exit {done['code']}: {done['err'].strip()[:80]}>"


def milestone_1(project):
    problems = []
    cli = Cli(project)
    if cli.ok("list") != "":
        problems.append("list on an empty store prints something")
    if cli.ok("add", "first") != "Added note 1\n":
        problems.append("first add does not print 'Added note 1'")
    if cli.ok("add", "second note", "--tag", "work", "--tag", "alpha") != "Added note 2\n":
        problems.append("second add does not print 'Added note 2'")
    if cli.ok("list") != "1\tfirst\t\n2\tsecond note\talpha,work\n":
        problems.append(f"list output is {cli.ok('list')!r}")
    if not (cli.cwd / "notes.json").is_file():
        problems.append("notes.json was not written in the working directory")
    return problems


def milestone_2(project):
    problems = []
    cli = Cli(project)
    for text in ("a", "b", "c"):
        cli("add", text)
    if cli.ok("delete", "2") != "Deleted note 2\n":
        problems.append("delete does not print 'Deleted note 2'")
    if cli.ok("list") != "1\ta\t\n3\tc\t\n":
        problems.append(f"list after delete is {cli.ok('list')!r}")
    missing = cli("delete", "9")
    if missing["code"] != 1 or missing["err"] != "Error: note 9 not found\n":
        problems.append(f"unknown id: exit {missing['code']}, stderr {missing['err']!r}")
    cli("delete", "3")
    if cli.ok("add", "d") != "Added note 4\n":
        problems.append("an id was reused after deleting the newest note")
    return problems


def milestone_3(project):
    problems = []
    cli = Cli(project)
    cli("add", "Buy MILK", "--tag", "home")
    cli("add", "call mum", "--tag", "Home")
    cli("add", "milkshake recipe", "--tag", "homework", "--tag", "food")
    if cli.ok("search", "milk") != "1\tBuy MILK\thome\n3\tmilkshake recipe\tfood,homework\n":
        problems.append(f"search output is {cli.ok('search', 'milk')!r}")
    if cli.ok("search", "zzz") != "":
        problems.append("search without matches prints something")
    if cli.ok("list", "--tag", "home") != "1\tBuy MILK\thome\n":
        problems.append(f"list --tag output is {cli.ok('list', '--tag', 'home')!r}")
    return problems


def milestone_4(project):
    problems = []
    cli = Cli(project)
    cli("add", "plain")
    cli("add", "tagged", "--tag", "z", "--tag", "a")
    if cli.ok("export", "--format", "md") != "# Notes\n\n- [1] plain\n- [2] tagged (tags: a, z)\n":
        problems.append(f"markdown export is {cli.ok('export', '--format', 'md')!r}")
    try:
        exported = json.loads(cli.ok("export", "--format", "json"))
    except json.JSONDecodeError:
        exported = None
    if exported != [{"id": 1, "text": "plain", "tags": []}, {"id": 2, "text": "tagged", "tags": ["a", "z"]}]:
        problems.append(f"json export is {exported!r}")
    if cli.ok("export", "--format", "md", "--output", "out.md") != "Exported 2 notes to out.md\n":
        problems.append("export --output does not print the confirmation line")
    written = read_text(cli.cwd / "out.md")
    # SPEC.md does not say whether the file ends with a newline, so both are accepted.
    if written is None or written.replace("\r\n", "\n").rstrip("\n") != "# Notes\n\n- [1] plain\n- [2] tagged (tags: a, z)":
        problems.append("export --output wrote the wrong content")
    if cli("export", "--format", "xml")["code"] != 2:
        problems.append("an unknown format is not rejected with exit code 2")
    return problems


def robustness(project):
    problems = []
    cli = Cli(project)
    store = cli.cwd / "notes.json"
    store.write_text("{not json", encoding="utf-8")
    for command in (["list"], ["add", "x"], ["delete", "1"], ["search", "x"], ["export", "--format", "md"]):
        done = cli(*command)
        if done["code"] != 1 or done["err"] != "Error: notes.json is corrupted\n":
            problems.append(f"{command[0]} on a corrupted store: exit {done['code']}, stderr {done['err'][:60]!r}")
    if store.read_text(encoding="utf-8") != "{not json":
        problems.append("the corrupted file was modified")
    return problems


def test_names(project):
    text = read_text(project / "test_notes.py")
    if text is None:
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    return {item.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            for item in node.body if isinstance(item, ast.FunctionDef) and item.name.startswith("test")}


def handoff_files(project):
    """Files, other than the spec, that mention both remaining milestones."""
    found = []
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project)
        if not path.is_file() or relative.as_posix() == "SPEC.md" or path.suffix in (".pyc", ".json"):
            continue
        if any(part in ("__pycache__", ".git") for part in relative.parts):
            continue
        text = read_text(path)
        if text and re.search(r"\bM3\b", text, re.IGNORECASE) and re.search(r"\bM4\b", text, re.IGNORECASE):
            found.append(relative.as_posix())
    return found


m1, m2, m3, m4, robust = milestone_1(WORK), milestone_2(WORK), milestone_3(WORK), milestone_4(WORK), robustness(WORK)
checks.add("m1-add-list", "R1", not m1, "; ".join(m1[:3]))
checks.add("m2-delete", "R2", not m2, "; ".join(m2[:3]))
checks.add("m3-search-filter", "R3", not m3, "; ".join(m3[:3]))
checks.add("m4-export", "R4", not m4, "; ".join(m4[:3]))
checks.add("corrupted-and-missing-store", "R5", not robust, "; ".join(robust[:3]))

names = test_names(WORK)
suite = run([sys.executable, "-m", "unittest", "test_notes"], WORK, timeout=180) if names is not None else {"code": 1, "err": "test_notes.py missing"}
tail = (suite.get("err") or "").strip().splitlines()[-1:] or [""]
checks.add("tests-pass", "R6", names is not None and suite["code"] == 0, tail[0][:200], kind="requirement")
test_text = (read_text(WORK / "test_notes.py") or "").lower()
covered = [word for word in ("add", "delete", "search", "export") if word in test_text]
checks.add("tests-cover-milestones", "R6", names is not None and len(names) >= 8 and len(covered) == 4,
           f"{len(names or [])} test methods; mentions {covered}", kind="requirement")

first_m1, first_m2 = milestone_1(FIRST), milestone_2(FIRST)
checks.add("session-1-delivers-m1-m2", "R7", not first_m1 and not first_m2, "; ".join((first_m1 + first_m2)[:3]), kind="process")
notes = handoff_files(FIRST)
checks.add("session-1-leaves-handoff", "R7", bool(notes), "files naming M3 and M4: " + (", ".join(notes[:4]) or "none"), kind="process")

first_names = test_names(FIRST) or set()
dropped = sorted(first_names - (names or set()))
checks.add("earlier-work-intact", "R8", not m1 and not m2 and not dropped,
           ("; ".join((m1 + m2)[:2]) + (" tests removed: " + ", ".join(dropped[:4]) if dropped else "")).strip(), kind="process")

checks.emit()
