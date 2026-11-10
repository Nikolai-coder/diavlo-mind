#!/usr/bin/env python3
"""External sequential orchestrator for DIAVLO MIND.

For models that have no native subagents, filesystem or shell: this script
plays the orchestrator, calls the model once per role (planner, executor,
reviewer), writes the files the model returns into a workspace, runs YOUR
check command and feeds failures back for repair.

    python dm_orchestrate.py --task task.md --workspace ./proj --mode standard \
        --executor claude-cli:haiku --check-cmd "python -m unittest -q"

    # Advisor mode: strong model plans and reviews, small model executes
    python dm_orchestrate.py --task task.md --workspace ./proj --mode deep \
        --advisor anthropic:<strong-model> --executor compatible:<local-model> \
        --check-cmd "python -m pytest -q"

Modes:
    raw       one call, no DIAVLO MIND rules (baseline for benchmarks)
    fast      one call with the rules, one repair if the check fails
    standard  plan -> execute -> check -> repair -> review
    deep      plan with several tasks -> execute each -> check -> repair -> review

Safety: the model never runs commands. Only the --check-cmd you supply is
executed. Files are written only inside the workspace.

Python 3.9+, standard library only. Providers: see dm_llm.py.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dm_llm  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".diavlo-mind", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".pytest_cache"}
PROTECTED = (".git", ".diavlo-mind")

FILE_PROTOCOL = """You cannot run tools or commands. To create or replace a file, write the whole file between marker lines:

=== FILE: relative/path.ext ===
<entire file content>
=== END FILE ===

To delete a file write one line:  === DELETE: relative/path.ext ===

Rules for files: paths are relative to the workspace root; always write the complete file, never a fragment or a diff; do not wrap file content in code fences; text outside the markers is not saved."""

RAW_SYSTEM = "You are an assistant that completes tasks by writing files into a workspace.\n\n" + FILE_PROTOCOL

FILE_RE = re.compile(r"^=== FILE: (.+?) ===[ \t]*\r?\n(.*?)\r?\n?^=== END FILE ===[ \t]*$", re.M | re.S)
DELETE_RE = re.compile(r"^=== DELETE: (.+?) ===[ \t]*$", re.M)


class OrchestrationError(Exception):
    pass


# --------------------------------------------------------------------------
# Prompt building
# --------------------------------------------------------------------------

def core_rules() -> str:
    """The ten rules, read from SKILL.md so there is one source of truth."""
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"<!-- dm:core-rules:start -->(.*?)<!-- dm:core-rules:end -->", text, re.S)
    if not match:
        raise OrchestrationError("core rules block not found in SKILL.md")
    return match.group(1).strip()


def planner_system(max_tasks: int) -> str:
    return f"""You are the PLANNER in a DIAVLO MIND team. Turn the task into a plan another model can execute without asking questions.

{core_rules()}

How to plan:
- Read the task and the workspace files given to you. Do not invent files that are not shown.
- Extract every explicit requirement as R1, R2, ... keeping numbers, names, formats and limits exactly. Add implied requirements (existing behaviour and tests keep working) marked "(implied)".
- Split the work into at most {max_tasks} task(s). Each task names the files it may write and has acceptance checks that can be run or inspected.
- Order tasks by dependency; put the riskiest first.

Return ONLY one JSON object, no prose before or after:
{{"objective": "<testable outcome>",
  "requirements": [{{"id": "R1", "text": "..."}}],
  "tasks": [{{"id": "T1", "title": "...", "instructions": "<precise instructions: what to build, interfaces, edge cases>",
             "files": ["path/it/may/write"], "acceptance": ["<check>"], "requirements": ["R1"]}}],
  "assumptions": ["..."],
  "questions": ["<only questions that block the work>"]}}"""


def executor_system() -> str:
    return f"""You are the EXECUTOR in a DIAVLO MIND team. Complete exactly the task you are given and nothing else.

{core_rules()}

{FILE_PROTOCOL}

How to work:
- Read the task, its requirements and the workspace files shown. Follow the style and conventions already present.
- Make the smallest change that satisfies every requirement. Write only the files the task allows.
- Handle the boundaries and error cases the requirements name. Add or update tests when the task asks for them.
- You cannot execute anything, so never claim that tests pass. The orchestrator runs the checks.

After the files, end with one JSON object:
{{"status": "PARTIAL", "summary": "<what you wrote, in up to 3 lines>",
  "evidence": [{{"requirement": "R1", "status": "not_verified", "level": "ASSUMED", "proof": "<where it is implemented>"}}],
  "assumptions": ["..."], "open_questions": ["..."]}}"""


def repair_system() -> str:
    return executor_system() + """

This is a REPAIR pass. A check failed or a reviewer found a blocker. Read the failure output literally. First write one line starting with "Root cause:" that explains the failure. Then write the corrected files in full. Fix the cause, not the symptom; do not delete or weaken tests to make them pass."""


def reviewer_system() -> str:
    return f"""You are the REVIEWER in a DIAVLO MIND team. You are independent of the author: you see the requirements, the files and the check output, never the author's reasoning.

{core_rules()}

How to review:
- For each requirement, find where it is implemented and whether the files really satisfy it, including boundaries and error cases.
- Look for wrong logic, unhandled errors, missing requirements, changes outside the task, and needless complexity.
- Report only findings you can point to in the files shown. Severity: blocker (requirement unmet, or correctness/security/data at risk), major, minor, note.
- You did not execute anything. Trust the check output shown for what it covers and nothing more.

Return ONLY one JSON object:
{{"verdict": "PASS" | "PASS_WITH_ISSUES" | "FAIL",
  "coverage": [{{"requirement": "R1", "covered": true, "where": "file:line", "note": ""}}],
  "findings": [{{"severity": "blocker", "where": "file:line", "finding": "...", "suggestion": "..."}}]}}"""


# --------------------------------------------------------------------------
# Workspace handling
# --------------------------------------------------------------------------

def snapshot(workspace: Path, per_file: int, total: int) -> str:
    """Text listing of the workspace: contents of small text files, names of the rest."""
    shown, omitted, used = [], [], 0
    for path in sorted(workspace.rglob("*")):
        relative = path.relative_to(workspace)
        if any(part in SKIP_DIRS for part in relative.parts) or not path.is_file():
            continue
        name = relative.as_posix()
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            omitted.append(f"{name} (binary or unreadable)")
            continue
        if len(raw) > per_file or used + len(raw) > total:
            omitted.append(f"{name} ({len(raw)} bytes, not shown)")
            continue
        used += len(raw)
        shown.append(f"--- {name} ({text.count(chr(10)) + 1} lines) ---\n{text}")
    parts = ["WORKSPACE FILES"]
    parts += shown or ["(the workspace is empty)"]
    if omitted:
        parts.append("Files present but not shown:\n" + "\n".join(f"  {line}" for line in omitted))
    return "\n\n".join(parts)


def safe_path(workspace: Path, relative: str) -> Path:
    relative = relative.strip().strip("`'\"")
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or candidate.drive or ".." in candidate.parts:
        raise OrchestrationError(f"refused unsafe path: {relative!r}")
    if candidate.parts and candidate.parts[0] in PROTECTED:
        raise OrchestrationError(f"refused protected path: {relative!r}")
    resolved = (workspace / candidate).resolve()
    root = workspace.resolve()
    if root != resolved and root not in resolved.parents:
        raise OrchestrationError(f"refused path outside the workspace: {relative!r}")
    return resolved


def strip_fence(content: str) -> str:
    lines = content.split("\n")
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return content


def drop_stale_bytecode(source: Path) -> None:
    """Remove cached bytecode for a rewritten Python file.

    Python trusts a .pyc when the source has the same size and the same
    modification second. A repair that changes one character within a second
    of the previous write would otherwise be tested against the old code.
    """
    if source.suffix != ".py":
        return
    for cached in (source.parent / "__pycache__").glob(source.stem + ".*.pyc"):
        try:
            cached.unlink()
        except OSError:
            pass


def apply_reply(workspace: Path, reply: str, dry_run: bool = False) -> Tuple[List[str], List[str]]:
    """Write the file blocks in a model reply. Returns (changed paths, problems)."""
    changed, problems = [], []
    blocks = FILE_RE.findall(reply)
    opened = len(re.findall(r"^=== FILE: ", reply, re.M))
    if opened > len(blocks):
        problems.append(f"{opened - len(blocks)} file block(s) were not closed with '=== END FILE ===' and were ignored "
                        "(the reply was probably cut off)")
    for name, content in blocks:
        try:
            target = safe_path(workspace, name)
        except OrchestrationError as exc:
            problems.append(str(exc))
            continue
        content = strip_fence(content.replace("\r\n", "\n"))
        if not content.endswith("\n"):
            content += "\n"
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
            drop_stale_bytecode(target)
        changed.append(target.relative_to(workspace.resolve()).as_posix())
    for name in DELETE_RE.findall(reply):
        try:
            target = safe_path(workspace, name)
        except OrchestrationError as exc:
            problems.append(str(exc))
            continue
        if target.is_file():
            if not dry_run:
                target.unlink()
            changed.append(target.relative_to(workspace.resolve()).as_posix() + " (deleted)")
    return changed, problems


def extract_json(text: str, required_key: str) -> Optional[dict]:
    """Last JSON object in the text that contains required_key (file blocks removed first)."""
    cleaned = FILE_RE.sub("", text)
    decoder = json.JSONDecoder()
    found = None
    index = cleaned.find("{")
    while index != -1:
        try:
            value, end = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            index = cleaned.find("{", index + 1)
            continue
        if isinstance(value, dict) and required_key in value:
            found = value
        index = cleaned.find("{", index + max(end, 1))
    return found


def run_check(command: Optional[str], workspace: Path, timeout: int) -> dict:
    if not command:
        return {"ran": False, "passed": None, "exit_code": None, "output": "", "command": None}
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        run = subprocess.run(command, shell=True, cwd=str(workspace), capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=timeout, env=environment)
        output, code = (run.stdout or "") + (run.stderr or ""), run.returncode
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
        output += f"\n[check timed out after {timeout}s]"
        code = 124
    return {"ran": True, "passed": code == 0, "exit_code": code, "output": output[-6000:], "command": command}


# --------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------

class Run:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.workspace = Path(args.workspace).resolve()
        if not self.workspace.is_dir():
            raise OrchestrationError(f"workspace does not exist: {self.workspace}")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.run_dir = Path(args.run_dir).resolve() if args.run_dir else self.workspace / ".diavlo-mind" / "runs" / stamp
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.executor = args.executor
        self.advisor = args.advisor or args.executor
        self.usage: Dict[str, Dict[str, float]] = {}
        self.calls = 0
        self.files_written: List[str] = []
        self.problems: List[str] = []
        self.repairs = 0
        self.escalations = 0

    # -- model calls -------------------------------------------------------
    def call(self, role: str, spec: str, system: str, prompt: str) -> str:
        if self.calls >= self.args.max_calls:
            raise OrchestrationError(f"call budget of {self.args.max_calls} reached")
        self.calls += 1
        result = dm_llm.complete(spec, system, [{"role": "user", "content": prompt}], self.args.max_tokens)
        bucket = self.usage.setdefault(role, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "seconds": 0.0})
        bucket["calls"] += 1
        bucket["input_tokens"] += result.get("input_tokens") or 0
        bucket["output_tokens"] += result.get("output_tokens") or 0
        bucket["cost_usd"] += result.get("cost_usd") or 0.0
        bucket["seconds"] += result.get("seconds") or 0.0
        with open(self.run_dir / "transcript.jsonl", "a", encoding="utf-8") as log:
            log.write(json.dumps({
                "n": self.calls, "role": role, "spec": spec, "system_chars": len(system), "prompt_chars": len(prompt),
                "reply": result["text"], "input_tokens": result.get("input_tokens"),
                "output_tokens": result.get("output_tokens"), "cost_usd": result.get("cost_usd"),
            }, ensure_ascii=False) + "\n")
        self.say(f"  {role} <- {spec}: {len(result['text'])} chars")
        return result["text"]

    def say(self, message: str) -> None:
        if not self.args.quiet:
            print(message, file=sys.stderr)

    def view(self) -> str:
        return snapshot(self.workspace, self.args.max_file_bytes, self.args.max_context_bytes)

    def apply(self, reply: str) -> List[str]:
        changed, problems = apply_reply(self.workspace, reply, self.args.dry_run)
        self.files_written += [c for c in changed if c not in self.files_written]
        self.problems += problems
        for line in problems:
            self.say(f"  warning: {line}")
        return changed

    # -- steps -------------------------------------------------------------
    def plan(self, task: str, max_tasks: int) -> dict:
        reply = self.call("planner", self.advisor, planner_system(max_tasks), f"TASK\n{task}\n\n{self.view()}")
        plan = extract_json(reply, "tasks")
        if not plan or not plan.get("tasks") or not plan.get("requirements"):
            self.say("  planner reply was not usable JSON; falling back to a single task")
            plan = {"objective": task.strip().splitlines()[0][:200],
                    "requirements": [{"id": "R1", "text": "Satisfy the task as written."}],
                    "tasks": [{"id": "T1", "title": "Complete the task", "instructions": task, "files": [],
                               "acceptance": [], "requirements": ["R1"]}],
                    "assumptions": ["planner output could not be parsed"], "questions": []}
        plan["tasks"] = plan["tasks"][:max_tasks]
        (self.run_dir / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
        return plan

    def packet(self, task: str, plan: dict, unit: dict) -> str:
        wanted = set(unit.get("requirements") or [r["id"] for r in plan["requirements"]])
        requirements = [r for r in plan["requirements"] if r["id"] in wanted] or plan["requirements"]
        lines = ["TASK PACKET", f"id: {unit.get('id', 'T1')}", "role: executor", f"objective: {unit.get('title', '')}",
                 "instructions:", str(unit.get("instructions", "")), "requirements:"]
        lines += [f"  - {r['id']}: {r['text']}" for r in requirements]
        lines.append("may write: " + (", ".join(unit.get("files") or []) or "files needed for this task only"))
        lines.append("acceptance:")
        lines += [f"  - {check}" for check in (unit.get("acceptance") or ["the orchestrator's check command passes"])]
        lines += ["", "ORIGINAL TASK (for reference)", task, "", self.view()]
        return "\n".join(lines)

    def repair_loop(self, task: str, requirements: List[dict], check: dict, reason: str) -> dict:
        """Ask for fixes until the check passes or the budget is spent."""
        attempt = 0
        while attempt < self.args.max_repairs and (check["passed"] is False or reason):
            attempt += 1
            self.repairs += 1
            self.say(f"repair {attempt}/{self.args.max_repairs}")
            prompt = "\n".join([
                "TASK", task, "", "REQUIREMENTS",
                "\n".join(f"  - {r['id']}: {r['text']}" for r in requirements), "",
                f"CHECK COMMAND: {check['command']}" if check["ran"] else "CHECK COMMAND: (none supplied)",
                f"CHECK EXIT CODE: {check['exit_code']}" if check["ran"] else "",
                "CHECK OUTPUT (most recent part):", check["output"] or "(no output)", "",
                ("REVIEWER BLOCKERS:\n" + reason) if reason else "", "", self.view(),
            ])
            self.apply(self.call("executor", self.executor, repair_system(), prompt))
            check = run_check(self.args.check_cmd, self.workspace, self.args.check_timeout)
            reason = ""
        if check["passed"] is False and self.advisor != self.executor and not self.args.no_escalation:
            self.escalations += 1
            self.say("escalating the failing check to the advisor")
            prompt = "\n".join([
                "The executor could not fix this after repeated attempts. You are taking over the repair.", "",
                "TASK", task, "", f"CHECK COMMAND: {check['command']}", f"CHECK EXIT CODE: {check['exit_code']}",
                "CHECK OUTPUT (most recent part):", check["output"] or "(no output)", "", self.view(),
            ])
            self.apply(self.call("advisor-escalation", self.advisor, repair_system(), prompt))
            check = run_check(self.args.check_cmd, self.workspace, self.args.check_timeout)
        return check

    def review(self, plan: dict, check: dict) -> dict:
        prompt = "\n".join([
            "REQUIREMENTS", "\n".join(f"  - {r['id']}: {r['text']}" for r in plan["requirements"]), "",
            f"CHECK COMMAND: {check['command']}" if check["ran"] else "CHECK: NOT RUN (no command supplied)",
            f"CHECK EXIT CODE: {check['exit_code']}" if check["ran"] else "",
            "CHECK OUTPUT (most recent part):" if check["ran"] else "", check["output"] if check["ran"] else "", "",
            self.view(),
        ])
        reply = self.call("reviewer", self.advisor, reviewer_system(), prompt)
        review = extract_json(reply, "verdict")
        if not review:
            review = {"verdict": "UNPARSED", "coverage": [], "findings": [
                {"severity": "note", "where": "", "finding": "reviewer reply was not valid JSON", "suggestion": ""}]}
        (self.run_dir / "review.json").write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")
        return review

    # -- modes -------------------------------------------------------------
    def execute(self, task: str) -> int:
        mode = self.args.mode
        self.say(f"mode {mode} · executor {self.executor} · advisor {self.advisor} · run dir {self.run_dir}")
        plan: dict = {"requirements": [{"id": "R1", "text": "Satisfy the task as written."}], "tasks": []}
        review: Optional[dict] = None

        if mode in ("raw", "fast"):
            system = RAW_SYSTEM if mode == "raw" else executor_system()
            self.apply(self.call("executor", self.executor, system, f"TASK\n{task}\n\n{self.view()}"))
            check = run_check(self.args.check_cmd, self.workspace, self.args.check_timeout)
            if mode == "fast" and check["passed"] is False and self.args.max_repairs > 0:
                saved, self.args.max_repairs = self.args.max_repairs, 1
                check = self.repair_loop(task, plan["requirements"], check, "")
                self.args.max_repairs = saved
        else:
            plan = self.plan(task, 1 if mode == "standard" else self.args.max_tasks)
            done = self.load_progress()
            for unit in plan["tasks"]:
                if unit.get("id") in done:
                    self.say(f"skipping {unit.get('id')} (already applied in this run directory)")
                    continue
                self.say(f"task {unit.get('id')}: {unit.get('title')}")
                self.apply(self.call("executor", self.executor, executor_system(), self.packet(task, plan, unit)))
                done.append(unit.get("id"))
                (self.run_dir / "progress.json").write_text(json.dumps({"applied": done}), encoding="utf-8")
            check = run_check(self.args.check_cmd, self.workspace, self.args.check_timeout)
            if check["passed"] is False:
                check = self.repair_loop(task, plan["requirements"], check, "")
            if not self.args.no_review:
                review = self.review(plan, check)
                blockers = [f for f in review.get("findings", []) if f.get("severity") == "blocker"]
                if blockers and self.repairs < self.args.max_repairs + 1:
                    reason = "\n".join(f"  - {b.get('where', '')}: {b.get('finding', '')} -> {b.get('suggestion', '')}" for b in blockers)
                    saved, self.args.max_repairs = self.args.max_repairs, 1
                    check = self.repair_loop(task, plan["requirements"], check, reason)
                    self.args.max_repairs = saved
                    review["rechecked_after_fix"] = True

        return self.finish(task, plan, check, review)

    def load_progress(self) -> List[str]:
        path = self.run_dir / "progress.json"
        if self.args.resume and path.is_file():
            return list(json.loads(path.read_text(encoding="utf-8")).get("applied", []))
        return []

    # -- reporting ---------------------------------------------------------
    def finish(self, task: str, plan: dict, check: dict, review: Optional[dict]) -> int:
        open_blockers = []
        if review and not review.get("rechecked_after_fix"):
            open_blockers = [f for f in review.get("findings", []) if f.get("severity") == "blocker"]
        if check["ran"] and check["passed"] and not open_blockers:
            status = "DONE"
        elif check["ran"] and not check["passed"]:
            status = "FAILED"
        else:
            status = "PARTIAL"
        summary = {
            "status": status, "mode": self.args.mode, "executor": self.executor, "advisor": self.advisor,
            "check": {k: check[k] for k in ("ran", "passed", "exit_code", "command")},
            "repairs": self.repairs, "escalations": self.escalations, "calls": self.calls,
            "files_written": self.files_written, "problems": self.problems, "usage": self.usage,
            "review_verdict": review.get("verdict") if review else None, "run_dir": str(self.run_dir),
        }
        (self.run_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        (self.run_dir / "report.md").write_text(self.report(task, plan, check, review, status), encoding="utf-8")
        self.say(f"status {status} · {self.calls} call(s) · {self.repairs} repair(s) · report: {self.run_dir / 'report.md'}")
        if self.args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            print(f"Status: {status}")
            print(f"Report: {self.run_dir / 'report.md'}")
        return 0 if status == "DONE" else 1

    def report(self, task: str, plan: dict, check: dict, review: Optional[dict], status: str) -> str:
        coverage = {c.get("requirement"): c for c in (review or {}).get("coverage", [])}
        lines = ["# DIAVLO MIND orchestration report", "",
                 f"Result: {len(self.files_written)} file(s) written in `{self.workspace}`",
                 f"Status: {status}", "",
                 f"- Mode: {self.args.mode}", f"- Executor: `{self.executor}`", f"- Advisor (plan, review, escalation): `{self.advisor}`",
                 f"- Model calls: {self.calls} · repairs: {self.repairs} · escalations to advisor: {self.escalations}", "",
                 "## Evidence", "", "| Req | Status | Evidence |", "|---|---|---|"]
        if check["ran"]:
            verdict = "passed" if check["passed"] else "FAILED"
            lines.append(f"| acceptance check | {verdict} — VERIFIED | `{check['command']}` → exit {check['exit_code']} (run by the orchestrator) |")
        else:
            lines.append("| acceptance check | not verified | NOT RUN: no --check-cmd was supplied |")
        for requirement in plan["requirements"]:
            seen = coverage.get(requirement["id"])
            text = requirement["text"].replace("|", "\\|")
            if seen is None:
                lines.append(f"| {requirement['id']} {text} | not verified | no review of this requirement |")
            else:
                state = "covered" if seen.get("covered") else "NOT covered"
                lines.append(f"| {requirement['id']} {text} | {state} — SOURCED | reviewer inspection: {seen.get('where') or '—'} {seen.get('note') or ''} |")
        lines += ["", "Requirement rows marked SOURCED come from a model reading the files, not from execution."]
        if review:
            lines += ["", f"## Review — verdict {review.get('verdict')}", ""]
            findings = review.get("findings", [])
            if findings:
                lines += ["| Severity | Where | Finding | Suggested fix |", "|---|---|---|---|"]
                lines += [f"| {f.get('severity', '')} | {f.get('where', '')} | {str(f.get('finding', '')).replace('|', '/')} | "
                          f"{str(f.get('suggestion', '')).replace('|', '/')} |" for f in findings]
            else:
                lines.append("No findings.")
            if review.get("rechecked_after_fix"):
                lines.append("\nBlockers were sent back for repair and the check was run again afterwards.")
            if self.advisor == self.executor:
                lines.append("\nThe reviewer was the same model in a fresh context, not a different model.")
        if check["ran"] and not check["passed"]:
            lines += ["", "## Failing check output (most recent part)", "", "```", check["output"].strip(), "```"]
        lines += ["", "## Files written", ""] + ([f"- `{name}`" for name in self.files_written] or ["- none"])
        if self.problems:
            lines += ["", "## Problems", ""] + [f"- {p}" for p in self.problems]
        if plan.get("assumptions"):
            lines += ["", "## Assumptions", ""] + [f"- {a}" for a in plan["assumptions"]]
        if plan.get("questions"):
            lines += ["", "## Open questions from the planner", ""] + [f"- {q}" for q in plan["questions"]]
        lines += ["", "## Usage", "", "| Role | Calls | Input tokens | Output tokens | Cost (USD, if reported) | Seconds |", "|---|---|---|---|---|---|"]
        for role, use in self.usage.items():
            lines.append(f"| {role} | {use['calls']} | {use['input_tokens']} | {use['output_tokens']} | {use['cost_usd']:.4f} | {use['seconds']:.1f} |")
        not_done = []
        if not check["ran"]:
            not_done.append("acceptance was not executed")
        if check["ran"] and not check["passed"]:
            not_done.append("the acceptance check still fails")
        lines += ["", "Not done / not verified: " + ("; ".join(not_done) or "nothing"),
                  "Next step: " + ("review the files and commit" if status == "DONE" else
                                   "read the failing output above, then rerun with a stronger --advisor or fix by hand" if status == "FAILED" else
                                   "run your acceptance check, or rerun with --check-cmd")]
        return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DIAVLO MIND sequential orchestrator", epilog="Providers: see dm_llm.py")
    parser.add_argument("--task", required=True, help="task text, or path to a file containing it")
    parser.add_argument("--workspace", required=True, help="directory the model's files are written into")
    parser.add_argument("--mode", choices=["raw", "fast", "standard", "deep"], default="standard")
    parser.add_argument("--executor", required=True, help="provider:model that writes the work")
    parser.add_argument("--advisor", help="provider:model for planning, review and escalation (default: the executor)")
    parser.add_argument("--check-cmd", help="command run in the workspace to verify the result (exit 0 = pass)")
    parser.add_argument("--check-timeout", type=int, default=300)
    parser.add_argument("--max-repairs", type=int, default=2)
    parser.add_argument("--max-tasks", type=int, default=6, help="task limit in deep mode")
    parser.add_argument("--max-calls", type=int, default=30, help="hard limit on model calls")
    parser.add_argument("--max-tokens", type=int, help="output token limit per call")
    parser.add_argument("--max-file-bytes", type=int, default=24_000)
    parser.add_argument("--max-context-bytes", type=int, default=160_000)
    parser.add_argument("--no-review", action="store_true")
    parser.add_argument("--no-escalation", action="store_true")
    parser.add_argument("--run-dir", help="where transcript, plan and report go (default: <workspace>/.diavlo-mind/runs/<time>)")
    parser.add_argument("--resume", action="store_true", help="with --run-dir: skip tasks already applied there")
    parser.add_argument("--dry-run", action="store_true", help="call the model but write no files")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    parser.add_argument("--quiet", action="store_true")
    return parser


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    args = build_parser().parse_args(argv)
    task_path = Path(args.task)
    try:
        task = task_path.read_text(encoding="utf-8") if len(args.task) < 1024 and task_path.is_file() else args.task
    except OSError:
        task = args.task
    started = time.time()
    try:
        code = Run(args).execute(task)
    except (OrchestrationError, dm_llm.LLMError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not args.quiet:
        print(f"elapsed {time.time() - started:.1f}s", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
