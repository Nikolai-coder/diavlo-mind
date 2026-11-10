#!/usr/bin/env python3
"""Benchmark harness for DIAVLO MIND.

Runs the tasks in evaluation/tasks/ with and without the framework and scores
each run with the task's hidden checks.

    # sanity: the checks fail on nothing and pass on the reference solutions
    python evaluation/run_benchmark.py --runner null
    python evaluation/run_benchmark.py --runner reference

    # Claude Code, small model, both arms, one trial per task
    python evaluation/run_benchmark.py --runner claude-code --model haiku --arms baseline diavlo-mind

    # any agent CLI that reads a prompt file and works in a directory
    python evaluation/run_benchmark.py --runner command --model my-model \
        --agent-cmd "my-agent --cwd {workspace} --prompt-file {prompt_file}"

    # a chat-only model through the bundled orchestrator
    python evaluation/run_benchmark.py --runner orchestrate --executor openai:<model-id>

Arms:
    baseline      the task prompt only
    diavlo-mind   the task prompt plus the DIAVLO MIND instructions (prompts/system/)

Workspaces are created in the system temp directory, outside this repository,
so the hidden checks and reference solutions are not next to the agent. Results
go to evaluation/runs/<label>/. Then: python evaluation/score.py evaluation/runs/<label>

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

EVAL = Path(__file__).resolve().parent
ROOT = EVAL.parent
TASKS = EVAL / "tasks"
sys.path.insert(0, str(EVAL / "lib"))
from quality import analyse  # noqa: E402

COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", ".pytest_cache")
STATUS_RE = re.compile(r"STATUS:\s*(COMPLETE|INCOMPLETE)", re.IGNORECASE)
CLAUDE_TOOLS = "Bash,Read,Edit,Write,Glob,Grep"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_tasks(selected: Optional[List[str]]) -> List[dict]:
    tasks = []
    for folder in sorted(p for p in TASKS.iterdir() if p.is_dir()):
        config = json.loads((folder / "task.json").read_text(encoding="utf-8"))
        config["dir"] = folder
        if not selected or config["id"] in selected or config["category"] in selected:
            tasks.append(config)
    if selected:
        known = {t["id"] for t in tasks} | {t["category"] for t in tasks}
        unknown = [name for name in selected if name not in known]
        if unknown:
            raise SystemExit(f"error: unknown task or category: {', '.join(unknown)}")
    return tasks


def dm_prompt(tier: str) -> str:
    path = ROOT / "prompts" / "system" / f"diavlo-mind-{tier}.md"
    if not path.is_file():
        raise SystemExit(f"error: prompt tier not found: {path}")
    return path.read_text(encoding="utf-8")


def empty_usage() -> dict:
    return {"input_tokens": None, "output_tokens": None, "cost_usd": None, "turns": None, "tool_calls": None}


# --------------------------------------------------------------------------
# Runners: each takes a stage and returns what happened
# --------------------------------------------------------------------------

def run_null(stage: dict, workspace: Path, prompt: str, ctx: dict) -> dict:
    return dict(empty_usage(), ok=True, final_message="", error=None)


def run_reference(stage: dict, workspace: Path, prompt: str, ctx: dict) -> dict:
    source = ctx["task"]["dir"] / "reference" / stage.get("workspace", "main")
    if source.is_dir():
        shutil.copytree(source, workspace, dirs_exist_ok=True, ignore=COPY_IGNORE)
    return dict(empty_usage(), ok=True, final_message="Reference solution copied.\nSTATUS: COMPLETE", error=None)


def run_claude_code(stage: dict, workspace: Path, prompt: str, ctx: dict) -> dict:
    binary = shutil.which("claude")
    if not binary:
        raise SystemExit("error: the `claude` command was not found on PATH")
    args = ctx["args"]
    command = [binary, "-p", "--output-format", "stream-json", "--verbose", "--model", args.model,
               "--permission-mode", "acceptEdits", "--allowedTools", CLAUDE_TOOLS,
               "--safe-mode", "--no-session-persistence", "--max-budget-usd", str(args.max_budget_usd)]
    if ctx["arm"] == "diavlo-mind":
        command += ["--append-system-prompt", ctx["dm_prompt"]]
    try:
        done = subprocess.run(command, input=prompt, cwd=str(workspace), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=ctx["timeout"])
    except subprocess.TimeoutExpired:
        return dict(empty_usage(), ok=False, final_message="", error=f"timed out after {ctx['timeout']}s")
    tool_calls, result = 0, None
    for line in done.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            content = (event.get("message") or {}).get("content") or []
            tool_calls += sum(1 for block in content if isinstance(block, dict) and block.get("type") == "tool_use")
        elif event.get("type") == "result":
            result = event
    if result is None:
        return dict(empty_usage(), ok=False, final_message="", error=f"no result event (exit {done.returncode}): {done.stderr[-300:]}")
    usage = result.get("usage") or {}
    input_tokens = sum(usage.get(key) or 0 for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return {
        "ok": not result.get("is_error"), "final_message": result.get("result") or "",
        "error": str(result.get("result"))[:300] if result.get("is_error") else None,
        "input_tokens": input_tokens, "output_tokens": usage.get("output_tokens"),
        "cost_usd": result.get("total_cost_usd"), "turns": result.get("num_turns"), "tool_calls": tool_calls,
        "models": sorted((result.get("modelUsage") or {}).keys()),
    }


def run_command(stage: dict, workspace: Path, prompt: str, ctx: dict) -> dict:
    template = ctx["args"].agent_cmd
    if not template:
        raise SystemExit("error: --runner command needs --agent-cmd")
    scratch = Path(tempfile.mkdtemp(prefix="dm-prompt-"))
    try:
        system_file = scratch / "system.md"
        system_file.write_text(ctx["dm_prompt"] if ctx["arm"] == "diavlo-mind" else "", encoding="utf-8")
        text = prompt
        if ctx["arm"] == "diavlo-mind" and "{system_file}" not in template:
            text = ctx["dm_prompt"] + "\n\n---\n\nTASK\n\n" + prompt
        prompt_file = scratch / "prompt.md"
        prompt_file.write_text(text, encoding="utf-8")
        command = template.format(prompt_file=str(prompt_file), workspace=str(workspace), system_file=str(system_file),
                                  model=ctx["args"].model or "")
        try:
            done = subprocess.run(command, shell=True, cwd=str(workspace), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=ctx["timeout"])
        except subprocess.TimeoutExpired:
            return dict(empty_usage(), ok=False, final_message="", error=f"timed out after {ctx['timeout']}s")
        return dict(empty_usage(), ok=done.returncode == 0, final_message=done.stdout,
                    error=None if done.returncode == 0 else f"exit {done.returncode}: {done.stderr[-300:]}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def run_orchestrate(stage: dict, workspace: Path, prompt: str, ctx: dict) -> dict:
    args = ctx["args"]
    if not args.executor:
        raise SystemExit("error: --runner orchestrate needs --executor provider:model")
    scratch = Path(tempfile.mkdtemp(prefix="dm-orch-"))
    try:
        prompt_file = scratch / "task.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        mode = "raw" if ctx["arm"] == "baseline" else args.dm_mode
        command = [sys.executable, str(ROOT / "scripts" / "dm_orchestrate.py"), "--task", str(prompt_file),
                   "--workspace", str(workspace), "--mode", mode, "--executor", args.executor,
                   "--run-dir", str(scratch / "run"), "--json", "--quiet"]
        if args.advisor and ctx["arm"] != "baseline":
            command += ["--advisor", args.advisor]
        if ctx["task"].get("public_check"):
            command += ["--check-cmd", ctx["task"]["public_check"]]
        try:
            done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=ctx["timeout"])
        except subprocess.TimeoutExpired:
            return dict(empty_usage(), ok=False, final_message="", error=f"timed out after {ctx['timeout']}s")
        try:
            summary = json.loads(done.stdout)
        except json.JSONDecodeError:
            return dict(empty_usage(), ok=False, final_message="", error=f"orchestrator failed (exit {done.returncode}): {done.stderr[-300:]}")
        usage = summary.get("usage", {})
        return {
            "ok": True, "final_message": "", "error": None,
            "input_tokens": sum(u.get("input_tokens") or 0 for u in usage.values()),
            "output_tokens": sum(u.get("output_tokens") or 0 for u in usage.values()),
            "cost_usd": sum(u.get("cost_usd") or 0 for u in usage.values()) or None,
            "turns": summary.get("calls"), "tool_calls": None,
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


RUNNERS = {"null": run_null, "reference": run_reference, "claude-code": run_claude_code,
           "command": run_command, "orchestrate": run_orchestrate}


# --------------------------------------------------------------------------
# One run of one task
# --------------------------------------------------------------------------

def changed_python_files(workspace: Path, seed: Optional[Path]) -> List[Path]:
    changed = []
    for path in workspace.rglob("*.py"):
        relative = path.relative_to(workspace)
        if any(part in ("__pycache__", ".git") for part in relative.parts):
            continue
        original = seed / relative if seed else None
        try:
            if original is None or not original.is_file() or original.read_bytes() != path.read_bytes():
                changed.append(path)
        except OSError:
            continue
    return changed


def run_checks(task: dict, check_dir: Path, snapshots: Path, workspaces: Dict[str, Path]) -> dict:
    """Run the task's hidden checks on scratch copies of the work.

    A check may run the agent's programs and tests, which can write files. Working on copies
    means the checks never alter the evidence, so scoring the same work twice gives the same
    answer whether it happens right after the run or later with --rescore.
    """
    scratch = Path(tempfile.mkdtemp(prefix="dm-check-"))
    try:
        copies: Dict[str, Path] = {}
        target: Optional[Path] = None
        for key, path in workspaces.items():
            if Path(path).is_dir():
                copies[key] = scratch / "work" / key
                shutil.copytree(path, copies[key], ignore=COPY_IGNORE)
                if Path(path).resolve() == Path(check_dir).resolve():
                    target = copies[key]
        if target is None:
            target = scratch / "work" / "_checked"
            if Path(check_dir).is_dir():
                shutil.copytree(check_dir, target, ignore=COPY_IGNORE)
            else:
                target.mkdir(parents=True)
        snapshot_copy = scratch / "snapshots"
        if Path(snapshots).is_dir():
            shutil.copytree(snapshots, snapshot_copy, ignore=COPY_IGNORE)
        env = dict(os.environ, DM_SNAPSHOTS=str(snapshot_copy), PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8",
                   DM_WORKSPACES=json.dumps({key: str(path) for key, path in copies.items()}))
        try:
            done = subprocess.run([sys.executable, str(task["dir"] / "checks" / "check.py"), str(target)],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, env=env)
            return {"checks": json.loads(done.stdout)["checks"], "error": None}
        except subprocess.TimeoutExpired:
            return {"checks": [], "error": "check script timed out"}
        except (json.JSONDecodeError, KeyError):
            return {"checks": [], "error": f"check script did not return JSON: {(done.stderr or done.stdout)[-300:]}"}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def metrics(task: dict, checks: List[dict]) -> dict:
    functional = [c for c in checks if c["kind"] == "functional"]
    by_requirement: Dict[str, List[bool]] = {}
    for check in checks:
        by_requirement.setdefault(check["requirement"], []).append(check["passed"])
    requirement_ids = [r["id"] for r in task["requirements"]]
    covered = [rid for rid in requirement_ids if by_requirement.get(rid) and all(by_requirement[rid])]
    required = [c for c in checks if c.get("required", True)]
    return {
        "success": bool(required) and all(c["passed"] for c in required),
        "passed": sum(1 for c in checks if c["passed"]),
        "total": len(checks),
        "functional_correctness": round(sum(c["passed"] for c in functional) / len(functional), 3) if functional else None,
        "requirement_coverage": round(len(covered) / len(requirement_ids), 3) if requirement_ids else None,
        "requirements_met": covered,
        "unresolved_errors": sum(1 for c in checks if not c["passed"]),
    }


def run_task(task: dict, arm: str, trial: int, args: argparse.Namespace, out_root: Path, prompt_text: str) -> dict:
    runner = RUNNERS[args.runner]
    root = Path(tempfile.mkdtemp(prefix="dm-bench-"))
    workspaces: Dict[str, Path] = {}
    seeds: Dict[str, Path] = {}
    snapshots = root / "snapshots"
    stage_records, stage_errors, final_message = [], [], ""
    totals = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "turns": 0, "tool_calls": 0}
    known = {key: False for key in totals}
    started = time.time()
    ctx = {"task": task, "arm": arm, "args": args, "dm_prompt": prompt_text,
           "timeout": args.timeout or task.get("timeout_seconds", 900)}
    try:
        for stage in task["stages"]:
            key = stage.get("workspace", "main")
            if key not in workspaces:
                workspaces[key] = root / "work" / key
                seed = task["dir"] / stage["seed"] if stage.get("seed") else None
                if seed and seed.is_dir():
                    shutil.copytree(seed, workspaces[key], ignore=COPY_IGNORE)
                    seeds[key] = seed
                else:
                    workspaces[key].mkdir(parents=True)
            workspace = workspaces[key]
            missing = []
            for item in stage.get("copy_in", []):
                source = workspaces.get(item["from"], root / "missing") / item["path"]
                if source.is_file():
                    target = workspace / item["as"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                else:
                    missing.append(f"{item['from']}/{item['path']}")
            if missing:
                stage_errors.append(f"{stage['id']}: skipped, input not produced by an earlier stage: {', '.join(missing)}")
                stage_records.append({"id": stage["id"], "skipped": True})
                continue
            prompt = (task["dir"] / stage["prompt"]).read_text(encoding="utf-8")
            stage_started = time.time()
            outcome = runner(stage, workspace, prompt, ctx)
            outcome["seconds"] = round(time.time() - stage_started, 1)
            if outcome.get("error"):
                stage_errors.append(f"{stage['id']}: {outcome['error']}")
            for name in totals:
                if outcome.get(name) is not None:
                    totals[name] += outcome[name]
                    known[name] = True
            final_message = outcome.get("final_message") or ""
            shutil.copytree(workspace, snapshots / stage["id"], ignore=COPY_IGNORE)
            record = {k: v for k, v in outcome.items() if k != "final_message"}
            record.update(id=stage["id"], final_message_tail=final_message[-1500:])
            stage_records.append(record)

        check_key = task.get("check_workspace", "main")
        if task.get("assemble"):
            workspaces[check_key] = root / "work" / check_key
            workspaces[check_key].mkdir(parents=True, exist_ok=True)
            for item in task["assemble"]:
                source = workspaces.get(item["from"], root / "missing") / item["path"]
                if source.is_file():
                    target = workspaces[check_key] / item["as"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
        check_dir = workspaces.get(check_key) or (root / "work" / check_key)
        check_dir.mkdir(parents=True, exist_ok=True)
        checked = run_checks(task, check_dir, snapshots, workspaces)
        result = metrics(task, checked["checks"])

        claims = STATUS_RE.findall(final_message[-2500:])
        claimed = claims[-1].upper() if claims else None
        python_files = [p for key, ws in workspaces.items() if not (task.get("assemble") and key == check_key)
                        for p in changed_python_files(ws, seeds.get(key))]
        result.update({
            "task": task["id"], "category": task["category"], "arm": arm, "trial": trial, "runner": args.runner,
            "model": args.model or args.executor or args.runner, "checks": checked["checks"], "check_error": checked["error"],
            "claimed": claimed, "overclaim": claimed == "COMPLETE" and not result["success"],
            "underclaim": claimed == "INCOMPLETE" and result["success"],
            "quality": analyse(python_files),
            "duration_s": round(time.time() - started, 1), "stage_errors": stage_errors, "stages": stage_records,
        })
        result.update({name: (round(value, 5) if isinstance(value, float) else value) if known[name] else None
                       for name, value in totals.items()})

        run_dir = out_root / task["id"] / arm / f"trial-{trial}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if args.keep_workspaces:
            for key, workspace in workspaces.items():
                if workspace.is_dir():
                    shutil.copytree(workspace, run_dir / "workspaces" / key, ignore=COPY_IGNORE, dirs_exist_ok=True)
            if snapshots.is_dir():
                shutil.copytree(snapshots, run_dir / "snapshots", ignore=COPY_IGNORE, dirs_exist_ok=True)
        return result
    finally:
        shutil.rmtree(root, ignore_errors=True)


def rescore(folder: Path, selected: Optional[List[str]], only: Optional[List[str]] = None) -> int:
    """Run the current checks again on workspaces saved with --keep-workspaces.

    Use it after correcting a check. The original check results stay in the
    result file under "checks_as_run", so a re-score never hides what a run
    was first scored as. With `only`, the outcome of just those check ids is
    replaced and every other check keeps the outcome it had: that is the right
    call after correcting specific checks, because nothing else can move.
    """
    tasks = {task["id"]: task for task in load_tasks(selected)}
    changed = done = 0
    for path in sorted(folder.rglob("result.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        task = tasks.get(result["task"])
        saved = path.parent / "workspaces"
        if task is None:
            continue
        if not saved.is_dir():
            print(f"{path.parent}: no saved workspaces, cannot re-score")
            continue
        workspaces = {p.name: p for p in saved.iterdir() if p.is_dir()}
        check_dir = workspaces.get(task.get("check_workspace", "main"))
        snapshots = path.parent / "snapshots"
        if check_dir is None or (len(task["stages"]) > 1 and not task.get("assemble") and not snapshots.is_dir()):
            print(f"{path.parent}: saved data is incomplete for this task, cannot re-score")
            continue
        checked = run_checks(task, check_dir, snapshots, workspaces)
        if checked["error"]:
            print(f"{path.parent}: {checked['error']}")
            continue
        fresh = checked["checks"]
        if only:
            replacement = {c["id"]: c for c in fresh if c["id"] in only}
            known = {c["id"] for c in result["checks"]}
            fresh = [replacement.get(c["id"], c) for c in result["checks"]] + \
                    [c for cid, c in replacement.items() if cid not in known]
        before = {c["id"]: c["passed"] for c in result["checks"]}
        after = {c["id"]: c["passed"] for c in fresh}
        result.setdefault("checks_as_run", result["checks"])
        result.setdefault("success_as_run", result["success"])
        result.update(metrics(task, fresh))
        if only:
            result["rescored_checks"] = sorted(set(result.get("rescored_checks", [])) | set(only))
        result.update(checks=fresh, rescored=now(),
                      overclaim=result.get("claimed") == "COMPLETE" and not result["success"],
                      underclaim=result.get("claimed") == "INCOMPLETE" and result["success"])
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        done += 1
        if before != after:
            changed += 1
            flipped = sorted(k for k in after if before.get(k) != after[k])
            print(f"{result['task']} {result['arm']} trial {result['trial']}: changed checks {flipped}; "
                  f"success {result['success_as_run']} -> {result['success']}")
    print(f"re-scored {done} run(s); {changed} changed")
    return 0


def tool_version(command: List[str]) -> Optional[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=30).stdout.strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the DIAVLO MIND benchmark.")
    parser.add_argument("--runner", choices=sorted(RUNNERS))
    parser.add_argument("--rescore", metavar="RUN_DIR", help="re-run the checks on workspaces saved with --keep-workspaces, then exit")
    parser.add_argument("--only", nargs="+", metavar="CHECK_ID",
                        help="with --rescore: replace the outcome of these checks only and keep every other check as it was")
    parser.add_argument("--first-trial", type=int, default=1, help="number of the first trial (to add trials to an earlier run)")
    parser.add_argument("--model", help="model alias or id for the claude-code and command runners")
    parser.add_argument("--arms", nargs="+", default=None, choices=["baseline", "diavlo-mind"])
    parser.add_argument("--tasks", nargs="+", help="task ids or categories (default: all)")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--prompt-tier", default="standard", choices=["micro", "compact", "standard"])
    parser.add_argument("--agent-cmd", help="command template for --runner command: {prompt_file} {workspace} {system_file} {model}")
    parser.add_argument("--executor", help="provider:model for --runner orchestrate")
    parser.add_argument("--advisor", help="provider:model used by the diavlo-mind arm of --runner orchestrate")
    parser.add_argument("--dm-mode", default="standard", choices=["fast", "standard", "deep"], help="orchestrator mode for the diavlo-mind arm")
    parser.add_argument("--max-budget-usd", type=float, default=1.5, help="per-stage spending cap for the claude-code runner")
    parser.add_argument("--timeout", type=int, help="seconds per stage (default: the task's own limit)")
    parser.add_argument("--label", help="name of the results folder (default: runner-model-timestamp)")
    parser.add_argument("--out", help="results directory (default: evaluation/runs/<label>)")
    parser.add_argument("--keep-workspaces", action="store_true", help="copy final workspaces into the results folder")
    return parser


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    args = build_parser().parse_args(argv)
    if args.rescore:
        return rescore(Path(args.rescore), args.tasks, args.only)
    if not args.runner:
        raise SystemExit("error: --runner is required (or use --rescore RUN_DIR)")
    if args.runner in ("null", "reference"):
        arms = [args.runner]
    else:
        arms = args.arms or ["baseline", "diavlo-mind"]
        if args.runner in ("claude-code",) and not args.model:
            raise SystemExit("error: --model is required for this runner")
    tasks = load_tasks(args.tasks)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = args.label or "-".join(filter(None, [args.runner, (args.model or args.executor or "").replace(":", "_").replace("/", "_"), stamp]))
    out_root = Path(args.out) if args.out else EVAL / "runs" / label
    out_root.mkdir(parents=True, exist_ok=True)
    prompt_text = dm_prompt(args.prompt_tier)
    meta = {
        "label": label, "started": now(), "runner": args.runner, "model": args.model, "executor": args.executor,
        "advisor": args.advisor, "arms": arms, "trials": args.trials, "first_trial": args.first_trial,
        "tasks": [t["id"] for t in tasks],
        "prompt_tier": args.prompt_tier, "prompt_characters": len(prompt_text),
        "framework_version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "python": platform.python_version(), "platform": platform.platform(),
        "claude_code_version": tool_version(["claude", "--version"]) if args.runner == "claude-code" else None,
        "agent_cmd": args.agent_cmd,
    }
    (out_root / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    failures = 0
    for task in tasks:
        for arm in arms:
            for trial in range(args.first_trial, args.first_trial + args.trials):
                print(f"{task['id']:<28} {arm:<12} trial {trial} ... ", end="", flush=True)
                result = run_task(task, arm, trial, args, out_root, prompt_text)
                cost = f" ${result['cost_usd']:.3f}" if result.get("cost_usd") else ""
                claim = f" claimed {result['claimed']}" if result["claimed"] else ""
                print(f"{'PASS' if result['success'] else 'fail'}  {result['passed']}/{result['total']} checks"
                      f"  {result['duration_s']:.0f}s{cost}{claim}" + ("  OVERCLAIM" if result["overclaim"] else ""))
                for line in result["stage_errors"]:
                    print(f"    stage problem: {line}")
                if result["check_error"]:
                    print(f"    check problem: {result['check_error']}")
                    failures += 1
    meta["finished"] = now()
    (out_root / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"\nresults: {out_root}\nnext:    python evaluation/score.py {out_root}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
