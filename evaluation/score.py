#!/usr/bin/env python3
"""Aggregate benchmark results into summary.json and SUMMARY.md.

    python evaluation/score.py evaluation/runs/<label> [more run folders ...] [--out DIR]

Every result.json under the given folders is included. Results are grouped by
model and arm. Nothing is estimated: a metric a runner did not report is shown
as "n/a".
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def load(folders: List[Path]) -> List[dict]:
    results = []
    for folder in folders:
        for path in sorted(folder.rglob("result.json")):
            try:
                results.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"warning: skipping {path}: {exc}", file=sys.stderr)
    return results


def reported_model(result: dict) -> str:
    """The model id the runner reported, when every stage agrees on one; otherwise the name that was requested."""
    reported = {name for stage in result.get("stages") or [] for name in stage.get("models") or []}
    return reported.pop() if len(reported) == 1 else str(result.get("model"))


def load_meta(folders: List[Path]) -> List[dict]:
    metas = []
    for folder in folders:
        for path in sorted(folder.rglob("meta.json")):
            try:
                meta = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            where = path.parent.relative_to(folder).as_posix()
            meta["folder"] = folder.name if where == "." else f"{folder.name}/{where}"
            metas.append(meta)
    return metas


def mean(values: List[Optional[float]]) -> Optional[float]:
    known = [v for v in values if v is not None]
    return round(statistics.fmean(known), 4) if known else None


def total(values: List[Optional[float]]) -> Optional[float]:
    known = [v for v in values if v is not None]
    return round(sum(known), 4) if known else None


def arm_metrics(runs: List[dict]) -> dict:
    claims_complete = [r for r in runs if r.get("claimed") == "COMPLETE"]
    by_task: Dict[str, List[bool]] = defaultdict(list)
    for run in runs:
        by_task[run["task"]].append(bool(run["success"]))
    trials = max(len(v) for v in by_task.values())
    return {
        "runs": len(runs),
        "tasks": len(by_task),
        "trials_per_task": trials,
        "success_rate": round(sum(r["success"] for r in runs) / len(runs), 4),
        # A run re-scored after a check was corrected keeps its first outcome in success_as_run.
        "success_rate_as_first_scored": round(sum(r.get("success_as_run", r["success"]) for r in runs) / len(runs), 4),
        "rescored_runs_changed": sum(1 for r in runs if "checks_as_run" in r and
                                     {c["id"]: c["passed"] for c in r["checks_as_run"]} != {c["id"]: c["passed"] for c in r["checks"]}),
        "tasks_solved_every_trial": sum(1 for v in by_task.values() if all(v)),
        "tasks_solved_some_trial": sum(1 for v in by_task.values() if any(v)),
        "checks_passed_rate": round(sum(r["passed"] for r in runs) / max(1, sum(r["total"] for r in runs)), 4),
        "functional_correctness": mean([r.get("functional_correctness") for r in runs]),
        "requirement_coverage": mean([r.get("requirement_coverage") for r in runs]),
        "unresolved_errors_per_run": mean([r.get("unresolved_errors") for r in runs]),
        "claimed_complete": len(claims_complete),
        "overclaims": sum(1 for r in runs if r.get("overclaim")),
        "no_status_line": sum(1 for r in runs if r.get("claimed") is None),
        "code_quality_proxy": mean([(r.get("quality") or {}).get("score") for r in runs]),
        "input_tokens_per_run": mean([r.get("input_tokens") for r in runs]),
        "output_tokens_per_run": mean([r.get("output_tokens") for r in runs]),
        "cost_usd_per_run": mean([r.get("cost_usd") for r in runs]),
        "cost_usd_total": total([r.get("cost_usd") for r in runs]),
        "turns_per_run": mean([r.get("turns") for r in runs]),
        "tool_calls_per_run": mean([r.get("tool_calls") for r in runs]),
        "seconds_per_run": mean([r.get("duration_s") for r in runs]),
        "stage_errors": sum(len(r.get("stage_errors") or []) for r in runs),
    }


def task_metrics(runs: List[dict]) -> dict:
    return {
        "category": runs[0]["category"],
        "runs": len(runs),
        "solved": sum(1 for r in runs if r["success"]),
        "solved_as_first_scored": sum(1 for r in runs if r.get("success_as_run", r["success"])),
        "checks": f"{sum(r['passed'] for r in runs)}/{sum(r['total'] for r in runs)}",
        "requirement_coverage": mean([r.get("requirement_coverage") for r in runs]),
        "overclaims": sum(1 for r in runs if r.get("overclaim")),
        "output_tokens": mean([r.get("output_tokens") for r in runs]),
        "cost_usd": mean([r.get("cost_usd") for r in runs]),
        "tool_calls": mean([r.get("tool_calls") for r in runs]),
        "seconds": mean([r.get("duration_s") for r in runs]),
        "failed_checks": sorted({c["id"] for r in runs for c in r.get("checks", []) if not c["passed"]}),
    }


def show(value: object, digits: int = 2, percent: bool = False) -> str:
    if value is None:
        return "n/a"
    if percent:
        return f"{float(value) * 100:.0f}%"
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return f"{value:,}" if isinstance(value, int) else str(value)


ROWS = [
    ("Runs", "runs", {}),
    ("Task success rate", "success_rate", {"percent": True}),
    ("Task success rate as first scored", "success_rate_as_first_scored", {"percent": True}),
    ("Runs whose checks changed on re-scoring", "rescored_runs_changed", {}),
    ("Checks passed", "checks_passed_rate", {"percent": True}),
    ("Functional correctness (mean)", "functional_correctness", {"percent": True}),
    ("Requirement coverage (mean)", "requirement_coverage", {"percent": True}),
    ("Unresolved errors per run", "unresolved_errors_per_run", {}),
    ("Runs claiming COMPLETE", "claimed_complete", {}),
    ("Overclaims (claimed COMPLETE, checks failed)", "overclaims", {}),
    ("Runs without a STATUS line", "no_status_line", {}),
    ("Code-quality proxy (0-1)", "code_quality_proxy", {}),
    ("Input tokens per run", "input_tokens_per_run", {"digits": 0}),
    ("Output tokens per run", "output_tokens_per_run", {"digits": 0}),
    ("Cost per run (USD, as reported by the runner)", "cost_usd_per_run", {"digits": 3}),
    ("Cost total (USD)", "cost_usd_total", {"digits": 2}),
    ("Turns per run", "turns_per_run", {"digits": 1}),
    ("Tool calls per run", "tool_calls_per_run", {"digits": 1}),
    ("Seconds per run", "seconds_per_run", {"digits": 0}),
    ("Tasks solved in every trial", "tasks_solved_every_trial", {}),
    ("Tasks solved in at least one trial", "tasks_solved_some_trial", {}),
]


def render(summary: dict) -> str:
    groups = summary["groups"]
    names = list(groups)
    lines = ["# Benchmark summary", "",
             f"Generated {summary['generated']} from {summary['runs']} run(s).", ""]
    if summary["meta"]:
        lines += ["| Run folder | Runner | Model requested | Arm(s) | Trials | Tasks | Prompt tier | Framework | Agent version | Started (UTC) |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
    for meta in summary["meta"]:
        first = meta.get("first_trial") or 1
        last = first + (meta.get("trials") or 1) - 1
        lines.append(f"| `{meta.get('folder')}` | {meta.get('runner')} | `{meta.get('model') or meta.get('executor')}` | "
                     f"{', '.join(meta.get('arms', []))} | {first if first == last else f'{first}-{last}'} | {len(meta.get('tasks', []))} | "
                     f"{meta.get('prompt_tier') if 'diavlo-mind' in meta.get('arms', []) else '—'} | "
                     f"{meta.get('framework_version')} | {meta.get('claude_code_version') or 'n/a'} | "
                     f"{meta.get('started')} |")
    trials = max(g["trials_per_task"] for g in groups.values())
    caution = ("With one trial per task these numbers describe single runs. They are not evidence of a general effect: "
               "models are not deterministic, and a difference of one task is within run-to-run variation. Repeat with "
               "`--trials 3` or more before drawing conclusions." if trials == 1 else
               f"With {trials} trials per task, a difference of one or two runs between configurations is still within "
               "run-to-run variation. Use `compare_runs.py` for the paired comparison and its sign test before drawing conclusions.")
    lines += ["", "## How to read this", "",
              f"- Each cell is measured from executed runs. Trials per task and arm: {trials}.",
              f"- {caution}",
              "- Success means every hidden check of a task passed. Requirement coverage is the share of a task's "
              "requirements whose checks all passed.",
              "- An overclaim is a run whose final message said `STATUS: COMPLETE` while a check failed.",
              "- \"As first scored\" is the outcome before any check was corrected and the saved workspaces were "
              "re-scored. When the two success rates are equal, no correction changed an outcome.",
              "- Cost is the figure the runner reported, not a bill.", "",
              "## By configuration", "", "| Metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for label, key, options in ROWS:
        lines.append(f"| {label} | " + " | ".join(show(groups[name].get(key), **options) for name in names) + " |")
    lines += ["", "## By task", ""]
    header = "| Task | Category | " + " | ".join(f"{name}: solved · checks · coverage · out tokens · cost" for name in names) + " |"
    lines += [header, "|---|---|" + "---|" * len(names)]
    for task in sorted(summary["tasks"]):
        per = summary["tasks"][task]
        cells = []
        for name in names:
            data = per.get(name)
            if not data:
                cells.append("—")
                continue
            first = data.get("solved_as_first_scored", data["solved"])
            note = f" (first scored {first}/{data['runs']})" if first != data["solved"] else ""
            cells.append(f"{data['solved']}/{data['runs']}{note} · {data['checks']} · {show(data['requirement_coverage'], percent=True)} · "
                         f"{show(data['output_tokens'], 0)} · {show(data['cost_usd'], 3)}")
        category = next(iter(per.values()))["category"]
        lines.append(f"| {task} | {category} | " + " | ".join(cells) + " |")
    lines += ["", "## Failed checks", ""]
    any_failed = False
    for task in sorted(summary["tasks"]):
        for name in names:
            failed = (summary["tasks"][task].get(name) or {}).get("failed_checks")
            if failed:
                any_failed = True
                lines.append(f"- **{task}** — {name}: {', '.join(failed)}")
    if not any_failed:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Score benchmark runs.")
    parser.add_argument("folders", nargs="+")
    parser.add_argument("--out", help="where to write summary.json and SUMMARY.md (default: the first folder)")
    args = parser.parse_args(argv)
    folders = [Path(f) for f in args.folders]
    for folder in folders:
        if not folder.is_dir():
            raise SystemExit(f"error: not a directory: {folder}")
    results = load(folders)
    if not results:
        raise SystemExit("error: no result.json files found")

    grouped: Dict[str, List[dict]] = defaultdict(list)
    for result in results:
        grouped[f"{reported_model(result)} · {result['arm']}"].append(result)
    tasks: Dict[str, Dict[str, dict]] = defaultdict(dict)
    for name, runs in grouped.items():
        by_task: Dict[str, List[dict]] = defaultdict(list)
        for run in runs:
            by_task[run["task"]].append(run)
        for task, task_runs in by_task.items():
            tasks[task][name] = task_metrics(task_runs)

    summary = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runs": len(results),
        "meta": load_meta(folders),
        "overall": {"success_rate": round(sum(r["success"] for r in results) / len(results), 4)},
        "groups": {name: arm_metrics(runs) for name, runs in sorted(grouped.items())},
        "tasks": tasks,
    }
    out = Path(args.out) if args.out else folders[0]
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text = render(summary)
    (out / "SUMMARY.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"written: {out / 'summary.json'} and {out / 'SUMMARY.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
