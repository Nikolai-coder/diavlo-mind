#!/usr/bin/env python3
"""Write a compact, publishable record of benchmark runs.

    python evaluation/export_results.py evaluation/runs/<label> --out evaluation/results/<name>

The runs folder holds everything, including saved workspaces. This command copies
only what a reader needs to check the numbers:

    runs.jsonl       one line per run: task, arm, trial, model, outcome, failed checks,
                     completion claim, tokens, cost, turns, tool calls, duration
    summary.json     aggregates from score.py
    SUMMARY.md       the same as tables
    COMPARISON.md    paired comparison from compare_runs.py (when both arms are present)

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_runs  # noqa: E402
import score  # noqa: E402

KEEP = ["task", "category", "arm", "trial", "runner", "model", "success", "passed", "total", "requirement_coverage",
        "unresolved_errors", "claimed", "overclaim", "underclaim", "input_tokens", "output_tokens", "cost_usd",
        "turns", "tool_calls", "duration_s", "stage_errors"]


def compact(result: dict) -> dict:
    """The fields of one run that are worth publishing."""
    record = {key: result.get(key) for key in KEEP}
    record["failed_checks"] = [{"id": c["id"], "requirement": c.get("requirement"), "detail": str(c.get("detail") or "")[:240]}
                               for c in result.get("checks", []) if not c["passed"]]
    if "checks_as_run" in result:
        record["success_as_first_scored"] = result.get("success_as_run")
        record["failed_checks_as_first_scored"] = [c["id"] for c in result["checks_as_run"] if not c["passed"]]
        record["rescored"] = result.get("rescored")
    record["model_reported"] = score.reported_model(result)
    quality = result.get("quality") or {}
    record["code_quality_proxy"] = quality.get("score")
    return record


def export(folder: Path, out: Path) -> dict:
    results = score.load([folder])
    if not results:
        raise SystemExit(f"error: no result.json under {folder}")
    out.mkdir(parents=True, exist_ok=True)
    records = sorted((compact(r) for r in results), key=lambda r: (r["model_reported"], r["task"], r["arm"], r["trial"]))
    with (out / "runs.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    with contextlib.redirect_stdout(io.StringIO()):
        score.main([str(folder), "--out", str(out)])
    arms = sorted({r["arm"] for r in records})
    models = sorted({str(r["model_reported"]) for r in records})
    compared = False
    if {"baseline", "diavlo-mind"} <= set(arms) and len(models) == 1:
        with contextlib.redirect_stdout(io.StringIO()):
            compare_runs.main([str(folder), "--arm-a", "baseline", "--arm-b", "diavlo-mind", "--out", str(out / "COMPARISON.md")])
        compared = True
    return {"runs": len(records), "arms": arms, "models": models, "compared": compared}


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Export a compact record of benchmark runs.")
    parser.add_argument("folder", help="a results folder written by run_benchmark.py")
    parser.add_argument("--out", required=True, help="folder to write the published files into")
    args = parser.parse_args(argv)
    folder, out = Path(args.folder), Path(args.out)
    if not folder.is_dir():
        raise SystemExit(f"error: not a folder: {folder}")
    done = export(folder, out)
    print(f"{done['runs']} run(s), model(s) {', '.join(done['models'])}, arm(s) {', '.join(done['arms'])} -> {out.as_posix()}/")
    print("wrote runs.jsonl, summary.json, SUMMARY.md" + (", COMPARISON.md" if done["compared"] else
          " (no COMPARISON.md: it needs both arms of exactly one model)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
