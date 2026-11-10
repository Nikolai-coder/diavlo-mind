#!/usr/bin/env python3
"""Project-state manager for DIAVLO MIND (AUTONOMOUS mode and long projects).

Keeps objective, requirements, tasks with dependencies, decisions and
checkpoints in <project>/.diavlo-mind/state.json so any session can resume.

    dm_state.py init --objective "..." --mode autonomous --done "pytest -q passes"
    dm_state.py req add "Export accepts --since YYYY-MM-DD"
    dm_state.py task add "Parse --since" --req R1 --accept "pytest -q" --depends T1
    dm_state.py next
    dm_state.py task set T1 --status done --evidence "pytest -q -> 6 passed"
    dm_state.py checkpoint "T1 done" --next "T2: apply the filter"
    dm_state.py report | resume | validate | done-check

Add --dir <project> to work on a project that is not the current directory.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dm_schema  # noqa: E402

STATE_DIR = ".diavlo-mind"
STATE_FILE = "state.json"
REPORT_FILE = "STATE.md"

MODES = ["FAST", "STANDARD", "DEEP", "AUTONOMOUS"]
ROLES = ["architect", "planner", "executor", "researcher", "reviewer", "validator", "optimizer", "orchestrator"]
TASK_STATUS = ["todo", "doing", "review", "done", "blocked", "dropped"]
REQ_STATUS = ["open", "met", "unmet", "waived"]
REQ_TYPES = ["functional", "constraint", "format", "quality", "process"]


class StateError(Exception):
    """A user-facing error: bad input or a rule of the framework was broken."""


def now() -> str:
    """UTC timestamp. DM_NOW overrides it for reproducible tests."""
    fixed = os.environ.get("DM_NOW")
    if fixed:
        return fixed
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_path(project: Path) -> Path:
    return project / STATE_DIR / STATE_FILE


def load(project: Path) -> dict:
    path = state_path(project)
    if not path.is_file():
        raise StateError(f"no state at {path} - run: dm_state.py init --objective \"...\"")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StateError(f"{path} is not valid JSON: {exc}") from exc


def save(project: Path, state: dict) -> None:
    state["updated"] = now()
    path = state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as tmp:
            json.dump(state, tmp, indent=2, ensure_ascii=False)
            tmp.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def next_id(items: List[dict], prefix: str) -> str:
    highest = 0
    for item in items:
        try:
            highest = max(highest, int(item["id"][len(prefix):]))
        except (KeyError, ValueError):
            continue
    return f"{prefix}{highest + 1}"


def find(items: List[dict], item_id: str, kind: str) -> dict:
    for item in items:
        if item["id"] == item_id:
            return item
    raise StateError(f"unknown {kind} id: {item_id}")


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

def find_cycle(tasks: List[dict]) -> Optional[List[str]]:
    """Return one dependency cycle as a list of ids, or None."""
    graph: Dict[str, List[str]] = {t["id"]: list(t.get("depends_on", [])) for t in tasks}
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {node: WHITE for node in graph}
    stack: List[str] = []

    def visit(node: str) -> Optional[List[str]]:
        colour[node] = GREY
        stack.append(node)
        for dep in graph.get(node, []):
            if dep not in colour:
                continue
            if colour[dep] == GREY:
                return stack[stack.index(dep):] + [dep]
            if colour[dep] == WHITE:
                found = visit(dep)
                if found:
                    return found
        stack.pop()
        colour[node] = BLACK
        return None

    for node in list(graph):
        if colour[node] == WHITE:
            found = visit(node)
            if found:
                return found
    return None


def ready_tasks(state: dict) -> List[dict]:
    """Tasks that can start now: status todo and every dependency finished."""
    status = {t["id"]: t["status"] for t in state["tasks"]}
    ready = []
    for task in state["tasks"]:
        if task["status"] != "todo":
            continue
        if all(status.get(dep) in ("done", "dropped") for dep in task.get("depends_on", [])):
            ready.append(task)
    return ready


def structural_errors(state: dict) -> List[str]:
    errors = dm_schema.validate(state, dm_schema.load_schema("state.schema.json"))
    if errors:
        return errors
    task_ids = [t["id"] for t in state["tasks"]]
    req_ids = [r["id"] for r in state["requirements"]]
    task_status = {t["id"]: t["status"] for t in state["tasks"]}
    for label, ids in (("task", task_ids), ("requirement", req_ids)):
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            errors.append(f"duplicate {label} id(s): {', '.join(duplicates)}")
    for task in state["tasks"]:
        for dep in task.get("depends_on", []):
            if dep not in task_ids:
                errors.append(f"{task['id']} depends on unknown task {dep}")
            elif dep == task["id"]:
                errors.append(f"{task['id']} depends on itself")
            elif task["status"] == "done" and task_status[dep] not in ("done", "dropped"):
                errors.append(f"{task['id']} is done but its dependency {dep} is {task_status[dep]}")
        for req in task.get("requirements", []):
            if req not in req_ids:
                errors.append(f"{task['id']} references unknown requirement {req}")
        if task["status"] == "done" and not task.get("evidence"):
            errors.append(f"{task['id']} is done without evidence")
        if task["status"] == "dropped" and not task.get("note"):
            errors.append(f"{task['id']} is dropped without a reason")
    cycle = find_cycle(state["tasks"])
    if cycle:
        errors.append("dependency cycle: " + " -> ".join(cycle))
    covered = {req for task in state["tasks"] if task["status"] != "dropped" for req in task.get("requirements", [])}
    for req in state["requirements"]:
        if req["status"] == "met" and not req.get("evidence"):
            errors.append(f"{req['id']} is met without evidence")
        if req["status"] == "waived" and not req.get("evidence"):
            errors.append(f"{req['id']} is waived without saying who waived it and why")
        if req["status"] in ("open", "unmet") and req["id"] not in covered and state["tasks"]:
            errors.append(f"{req['id']} is not covered by any task")
    return errors


def completion_gaps(state: dict) -> List[str]:
    """What still stands between the project and DONE."""
    gaps = structural_errors(state)
    if not state["requirements"]:
        gaps.append("no requirements recorded - nothing can be proven")
    for req in state["requirements"]:
        if req["status"] not in ("met", "waived"):
            gaps.append(f"{req['id']} is {req['status']}: {req['text']}")
    for task in state["tasks"]:
        if task["status"] not in ("done", "dropped"):
            gaps.append(f"{task['id']} is {task['status']}: {task['title']}")
    return gaps


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def _cell(text: object) -> str:
    return str(text if text not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def render_report(state: dict) -> str:
    tasks, reqs = state["tasks"], state["requirements"]
    done = sum(1 for t in tasks if t["status"] == "done")
    met = sum(1 for r in reqs if r["status"] == "met")
    lines = [
        "# Project state",
        "",
        "> Generated by `dm_state.py report`. Edit state through the script, not this file.",
        "",
        f"**Objective:** {state['objective']}",
        f"**Mode:** {state['mode']}",
        f"**Updated:** {state['updated']}",
        f"**Progress:** {done} of {len(tasks)} tasks done · {met} of {len(reqs)} requirements met",
        "",
        "## Definition of done",
    ]
    lines += [f"- [ ] {item}" for item in state["definition_of_done"]] or ["- (none recorded)"]
    lines += ["", "## Requirements", "| ID | Requirement | Type | Status | Evidence |", "|---|---|---|---|---|"]
    for req in reqs:
        lines.append(f"| {req['id']} | {_cell(req['text'])} | {req['type']} | {req['status']} | {_cell(req.get('evidence'))} |")
    lines += ["", "## Tasks", "| ID | Title | Owner | Status | Depends on | Covers | Acceptance | Evidence |",
              "|---|---|---|---|---|---|---|---|"]
    for task in tasks:
        lines.append(
            f"| {task['id']} | {_cell(task['title'])} | {task['owner']} | {task['status']} | "
            f"{_cell(', '.join(task.get('depends_on', [])))} | {_cell(', '.join(task.get('requirements', [])))} | "
            f"{_cell(task.get('acceptance'))} | {_cell(task.get('evidence') or task.get('note'))} |"
        )
    lines += ["", "## Decisions", "| ID | Date | Decision | Why | Revisit if |", "|---|---|---|---|---|"]
    for decision in state["decisions"]:
        lines.append(
            f"| {decision['id']} | {decision['date']} | {_cell(decision['decision'])} | "
            f"{_cell(decision.get('why'))} | {_cell(decision.get('revisit_if'))} |"
        )
    lines += ["", "## Last checkpoint"]
    if state["checkpoints"]:
        last = state["checkpoints"][-1]
        lines += [
            f"- **When:** {last['time']} ({last['id']})",
            f"- **Summary:** {last['summary']}",
            f"- **Next action:** {last.get('next') or '—'}",
            f"- **Open questions:** {'; '.join(last.get('open_questions', [])) or 'none'}",
        ]
    else:
        lines.append("- (no checkpoint yet)")
    blocked = [t for t in tasks if t["status"] == "blocked"]
    if blocked:
        lines += ["", "## Blocked", "| Task | Needs |", "|---|---|"]
        lines += [f"| {t['id']} | {_cell(t.get('note'))} |" for t in blocked]
    return "\n".join(lines) + "\n"


def render_resume(state: dict) -> str:
    tasks = state["tasks"]
    by_status = lambda s: [t for t in tasks if t["status"] == s]  # noqa: E731
    lines = [
        "RESUME BRIEF",
        f"Objective: {state['objective']}",
        f"Mode: {state['mode']}   Updated: {state['updated']}",
        "Definition of done: " + ("; ".join(state["definition_of_done"]) or "(none recorded)"),
        f"Progress: {len(by_status('done'))} of {len(tasks)} tasks done; "
        f"{sum(1 for r in state['requirements'] if r['status'] == 'met')} of {len(state['requirements'])} requirements met",
    ]
    if state["checkpoints"]:
        last = state["checkpoints"][-1]
        lines += [f"Last checkpoint ({last['time']}): {last['summary']}",
                  f"  Next action recorded: {last.get('next') or '(none)'}"]
        for question in last.get("open_questions", []):
            lines.append(f"  Open question: {question}")
    else:
        lines.append("Last checkpoint: none")

    def section(title: str, items: List[dict], detail: str) -> None:
        lines.append(f"{title}: " + ("none" if not items else ""))
        for task in items:
            extra = task.get(detail)
            lines.append(f"  {task['id']} {task['title']}" + (f" — {extra}" if extra else ""))

    section("In progress (verify before trusting)", by_status("doing") + by_status("review"), "note")
    section("Ready to start", ready_tasks(state), "acceptance")
    section("Blocked", by_status("blocked"), "note")
    repeated = [t for t in tasks if t.get("attempts", 0) >= 2 and t["status"] not in ("done", "dropped")]
    for task in repeated:
        lines.append(f"Warning: {task['id']} has failed {task['attempts']} times - change approach or escalate.")
    lines.append("First step: verify the claims above against the real files and tests (workflows/protocols/recovery.md).")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace, project: Path) -> int:
    path = state_path(project)
    if path.exists() and not args.force:
        raise StateError(f"{path} already exists - use --force to replace it")
    stamp = now()
    state = {
        "schema_version": 1,
        "project": args.project or project.resolve().name,
        "objective": args.objective,
        "mode": args.mode.upper(),
        "created": stamp,
        "updated": stamp,
        "definition_of_done": list(args.done or []),
        "requirements": [],
        "tasks": [],
        "decisions": [],
        "checkpoints": [],
    }
    save(project, state)
    print(f"initialized {path}")
    return 0


def cmd_req(args: argparse.Namespace, project: Path) -> int:
    state = load(project)
    reqs = state["requirements"]
    if args.action == "add":
        req = {"id": next_id(reqs, "R"), "text": args.text, "type": args.type, "source": args.source, "status": "open"}
        reqs.append(req)
        save(project, state)
        print(req["id"])
    elif args.action == "set":
        req = find(reqs, args.id, "requirement")
        if args.text:
            req["text"] = args.text
        if args.evidence:
            req["evidence"] = args.evidence
        if args.status:
            if args.status in ("met", "waived") and not req.get("evidence"):
                raise StateError(f"{req['id']}: status '{args.status}' needs --evidence (rule 6: prove, don't claim)")
            req["status"] = args.status
        save(project, state)
        print(f"{req['id']} {req['status']}")
    else:
        for req in reqs:
            print(f"{req['id']}\t{req['status']}\t{req['type']}\t{req['text']}")
    return 0


def cmd_task(args: argparse.Namespace, project: Path) -> int:
    state = load(project)
    tasks = state["tasks"]
    if args.action == "add":
        task_ids = {t["id"] for t in tasks}
        req_ids = {r["id"] for r in state["requirements"]}
        for dep in args.depends or []:
            if dep not in task_ids:
                raise StateError(f"unknown dependency: {dep}")
        for req in args.req or []:
            if req not in req_ids:
                raise StateError(f"unknown requirement: {req}")
        task = {
            "id": next_id(tasks, "T"), "title": args.title, "owner": args.owner, "status": "todo",
            "depends_on": list(args.depends or []), "requirements": list(args.req or []), "attempts": 0,
        }
        if args.accept:
            task["acceptance"] = args.accept
        if args.files:
            task["files"] = list(args.files)
        if args.milestone:
            task["milestone"] = args.milestone
        tasks.append(task)
        save(project, state)
        print(task["id"])
    elif args.action == "set":
        task = find(tasks, args.id, "task")
        previous = task["status"]
        if args.owner:
            task["owner"] = args.owner
        if args.evidence:
            task["evidence"] = args.evidence
        if args.note:
            task["note"] = args.note
        if args.status:
            if args.status == "done" and not task.get("evidence"):
                raise StateError(f"{task['id']}: 'done' needs --evidence (rule 6: prove, don't claim)")
            if args.status == "dropped" and not task.get("note"):
                raise StateError(f"{task['id']}: 'dropped' needs --note with the reason")
            if args.status == "doing":
                status = {t["id"]: t["status"] for t in tasks}
                waiting = [d for d in task.get("depends_on", []) if status.get(d) not in ("done", "dropped")]
                if waiting:
                    raise StateError(f"{task['id']} cannot start: waiting for {', '.join(waiting)}")
            if args.status == "todo" and previous in ("doing", "review"):
                task["attempts"] = task.get("attempts", 0) + 1
            task["status"] = args.status
        save(project, state)
        print(f"{task['id']} {task['status']}")
        if task.get("attempts", 0) >= 2 and task["status"] == "todo":
            print(f"warning: {task['id']} has failed {task['attempts']} times - split it, change approach "
                  "or escalate; do not retry unchanged (rule 7)", file=sys.stderr)
    else:
        for task in tasks:
            if args.status and task["status"] != args.status:
                continue
            deps = ",".join(task.get("depends_on", [])) or "-"
            print(f"{task['id']}\t{task['status']}\t{task['owner']}\t{deps}\t{task['title']}")
    return 0


def cmd_next(args: argparse.Namespace, project: Path) -> int:
    state = load(project)
    ready = ready_tasks(state)
    if not ready:
        open_tasks = [t for t in state["tasks"] if t["status"] not in ("done", "dropped")]
        print("nothing ready" + (f" ({len(open_tasks)} task(s) still open - check blocked or doing)" if open_tasks else " - all tasks finished"))
        return 0
    writers: Dict[str, str] = {}
    for task in ready:
        clash = [f for f in task.get("files", []) if f in writers]
        marker = f"  [conflicts with {writers[clash[0]]} on {clash[0]} - do not run in parallel]" if clash else ""
        for path in task.get("files", []):
            writers.setdefault(path, task["id"])
        accept = f" — accept: {task['acceptance']}" if task.get("acceptance") else ""
        print(f"{task['id']}\t{task['owner']}\t{task['title']}{accept}{marker}")
    return 0


def cmd_decision(args: argparse.Namespace, project: Path) -> int:
    state = load(project)
    decision = {"id": next_id(state["decisions"], "D"), "date": now()[:10], "decision": args.text}
    for key in ("why", "alternatives", "revisit_if"):
        value = getattr(args, key)
        if value:
            decision[key] = value
    state["decisions"].append(decision)
    save(project, state)
    print(decision["id"])
    return 0


def cmd_dod(args: argparse.Namespace, project: Path) -> int:
    state = load(project)
    state["definition_of_done"].append(args.text)
    save(project, state)
    print(f"definition of done: {len(state['definition_of_done'])} item(s)")
    return 0


def cmd_checkpoint(args: argparse.Namespace, project: Path) -> int:
    state = load(project)
    checkpoint = {"id": next_id(state["checkpoints"], "C"), "time": now(), "summary": args.summary}
    if args.next:
        checkpoint["next"] = args.next
    if args.question:
        checkpoint["open_questions"] = list(args.question)
    state["checkpoints"].append(checkpoint)
    save(project, state)
    (project / STATE_DIR / REPORT_FILE).write_text(render_report(state), encoding="utf-8")
    print(f"{checkpoint['id']} saved; {REPORT_FILE} updated")
    return 0


def cmd_report(args: argparse.Namespace, project: Path) -> int:
    state = load(project)
    target = project / STATE_DIR / REPORT_FILE
    target.write_text(render_report(state), encoding="utf-8")
    done = sum(1 for t in state["tasks"] if t["status"] == "done")
    print(f"wrote {target} ({done} of {len(state['tasks'])} tasks done)")
    return 0


def cmd_resume(args: argparse.Namespace, project: Path) -> int:
    sys.stdout.write(render_resume(load(project)))
    return 0


def cmd_validate(args: argparse.Namespace, project: Path) -> int:
    errors = structural_errors(load(project))
    for line in errors:
        print(f"error: {line}")
    print("state is consistent" if not errors else f"{len(errors)} problem(s)")
    return 0 if not errors else 1


def cmd_done_check(args: argparse.Namespace, project: Path) -> int:
    state = load(project)
    gaps = completion_gaps(state)
    for line in gaps:
        print(f"not done: {line}")
    if gaps:
        print(f"NOT DONE - {len(gaps)} gap(s)")
        return 1
    print("DONE - every requirement is met or waived with evidence, every task is done or dropped.")
    for item in state["definition_of_done"]:
        print(f"confirm by running: {item}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dir", default=argparse.SUPPRESS, help="project directory (default: current directory)")

    parser = argparse.ArgumentParser(description="DIAVLO MIND project-state manager", parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", parents=[common], help="create .diavlo-mind/state.json")
    p.add_argument("--objective", required=True)
    p.add_argument("--mode", default="AUTONOMOUS", type=str.upper, choices=MODES)
    p.add_argument("--project")
    p.add_argument("--done", action="append", help="definition-of-done check (repeatable)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("req", parents=[common], help="requirements: add | set | list")
    rsub = p.add_subparsers(dest="action", required=True)
    a = rsub.add_parser("add", parents=[common])
    a.add_argument("text")
    a.add_argument("--type", default="functional", choices=REQ_TYPES)
    a.add_argument("--source", default="user")
    s = rsub.add_parser("set", parents=[common])
    s.add_argument("id")
    s.add_argument("--status", choices=REQ_STATUS)
    s.add_argument("--evidence")
    s.add_argument("--text")
    rsub.add_parser("list", parents=[common])
    p.set_defaults(func=cmd_req)

    p = sub.add_parser("task", parents=[common], help="tasks: add | set | list")
    tsub = p.add_subparsers(dest="action", required=True)
    a = tsub.add_parser("add", parents=[common])
    a.add_argument("title")
    a.add_argument("--owner", default="executor", choices=ROLES)
    a.add_argument("--req", action="append", help="requirement id covered (repeatable)")
    a.add_argument("--depends", action="append", help="task id this depends on (repeatable)")
    a.add_argument("--accept", help="acceptance check")
    a.add_argument("--files", action="append", help="path this task may write (repeatable)")
    a.add_argument("--milestone")
    s = tsub.add_parser("set", parents=[common])
    s.add_argument("id")
    s.add_argument("--status", choices=TASK_STATUS)
    s.add_argument("--evidence")
    s.add_argument("--note")
    s.add_argument("--owner", choices=ROLES)
    lst = tsub.add_parser("list", parents=[common])
    lst.add_argument("--status", choices=TASK_STATUS)
    p.set_defaults(func=cmd_task)

    p = sub.add_parser("next", parents=[common], help="tasks ready to start")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("decision", parents=[common], help="record a decision")
    p.add_argument("text")
    p.add_argument("--why")
    p.add_argument("--alternatives")
    p.add_argument("--revisit-if", dest="revisit_if")
    p.set_defaults(func=cmd_decision)

    p = sub.add_parser("dod", parents=[common], help="add a definition-of-done check")
    p.add_argument("text")
    p.set_defaults(func=cmd_dod)

    p = sub.add_parser("checkpoint", parents=[common], help="save a checkpoint")
    p.add_argument("summary")
    p.add_argument("--next")
    p.add_argument("--question", action="append", help="open question (repeatable)")
    p.set_defaults(func=cmd_checkpoint)

    for name, func, text in (
        ("report", cmd_report, "write STATE.md"),
        ("resume", cmd_resume, "print a brief for a fresh session"),
        ("validate", cmd_validate, "check structure, dependencies and coverage"),
        ("done-check", cmd_done_check, "exit 0 only when everything is proven"),
    ):
        p = sub.add_parser(name, parents=[common], help=text)
        p.set_defaults(func=func)
    return parser


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    args = build_parser().parse_args(argv)
    project = Path(getattr(args, "dir", "."))
    try:
        return args.func(args, project)
    except StateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
