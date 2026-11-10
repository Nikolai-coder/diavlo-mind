#!/usr/bin/env python3
"""Self-test of the benchmark: do the hidden checks discriminate?

For every task it runs two fake agents through the real harness:

    null       does nothing            -> the task must NOT count as solved
    reference  copies reference/       -> every check must pass

It also verifies that each requirement listed in task.json is covered by at
least one check and that check ids are unique. No model is called.

    python evaluation/selftest.py            # exit 1 if any task misbehaves
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_benchmark  # noqa: E402


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tasks", nargs="+", help="task ids or categories (default: all)")
    selected = parser.parse_args().tasks
    out = Path(tempfile.mkdtemp(prefix="dm-selftest-"))
    problems = []
    try:
        print(f"{'task':<30}{'null':<16}{'reference':<16}{'requirements covered'}")
        for task in run_benchmark.load_tasks(selected):
            row = {}
            for runner in ("null", "reference"):
                args = argparse.Namespace(runner=runner, model=None, executor=None, advisor=None, agent_cmd=None,
                                          timeout=None, keep_workspaces=False, max_budget_usd=0, dm_mode="standard")
                row[runner] = run_benchmark.run_task(task, runner, 1, args, out / runner, "")
            null, reference = row["null"], row["reference"]
            if null["check_error"] or reference["check_error"]:
                problems.append(f"{task['id']}: check script error: {null['check_error'] or reference['check_error']}")
            if null["success"]:
                problems.append(f"{task['id']}: an empty submission counts as solved")
            if null["total"] and null["passed"] / null["total"] > 0.5:
                problems.append(f"{task['id']}: an empty submission passes {null['passed']}/{null['total']} checks")
            if not reference["success"]:
                failed = [c["id"] for c in reference["checks"] if not c["passed"]]
                problems.append(f"{task['id']}: the reference solution fails {failed}")
            ids = [c["id"] for c in reference["checks"]]
            if len(ids) != len(set(ids)):
                problems.append(f"{task['id']}: duplicate check ids")
            checked = {c["requirement"] for c in reference["checks"]}
            declared = [r["id"] for r in task["requirements"]]
            unchecked = [r for r in declared if r not in checked]
            unknown = sorted(checked - set(declared))
            if unchecked:
                problems.append(f"{task['id']}: requirements without a check: {unchecked}")
            if unknown:
                problems.append(f"{task['id']}: checks refer to undeclared requirements: {unknown}")
            print(f"{task['id']:<30}{null['passed']}/{null['total']:<14}{reference['passed']}/{reference['total']:<14}"
                  f"{len(declared) - len(unchecked)}/{len(declared)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)
    print()
    for line in problems:
        print(f"PROBLEM: {line}")
    print("self-test passed: the checks reject empty work and accept the reference solutions" if not problems
          else f"self-test FAILED with {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
