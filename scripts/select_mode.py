#!/usr/bin/env python3
"""Recommend a DIAVLO MIND execution mode from explicit task signals.

The rules mirror the mode table in SKILL.md so that a person, a script or an
external orchestrator reaches the same answer from the same inputs.

Example:
    python select_mode.py --steps 6 --files 4 --unknowns 1
    python select_mode.py --steps 3 --files 2 --risk irreversible --json
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List

RISK_LEVELS = ["none", "moderate", "high", "irreversible"]
AMBIGUITY_LEVELS = ["none", "some", "high"]

ARTIFACTS = {
    "FAST": ["result", "one-line check"],
    "STANDARD": ["requirement list", "3-7 step plan", "executed checks", "delivery report"],
    "DEEP": [
        "requirement list with acceptance criteria",
        "investigation notes with sources",
        "options and decision record",
        "task plan with checks",
        "test or check output",
        "independent review findings",
        "validation report",
    ],
    "AUTONOMOUS": [
        "everything in DEEP",
        "definition of done",
        ".diavlo-mind/state.json with task graph",
        "checkpoints",
        "progress reports",
        "integration checks",
    ],
}

MODE_FILE = {
    "FAST": "workflows/modes/fast.md",
    "STANDARD": "workflows/modes/standard.md",
    "DEEP": "workflows/modes/deep.md",
    "AUTONOMOUS": "workflows/modes/autonomous.md",
}


def recommend(
    steps: int = 1,
    files: int = 1,
    components: int = 1,
    unknowns: int = 0,
    risk: str = "none",
    sessions: int = 1,
    prior_failures: int = 0,
    ambiguity: str = "none",
) -> Dict[str, object]:
    """Return the recommended mode with the reasons that fired."""
    if risk not in RISK_LEVELS:
        raise ValueError(f"risk must be one of {RISK_LEVELS}")
    if ambiguity not in AMBIGUITY_LEVELS:
        raise ValueError(f"ambiguity must be one of {AMBIGUITY_LEVELS}")
    for name, value in (("steps", steps), ("files", files), ("components", components),
                        ("unknowns", unknowns), ("sessions", sessions),
                        ("prior_failures", prior_failures)):
        if value < 0:
            raise ValueError(f"{name} cannot be negative")

    reasons: List[str] = []

    autonomous = []
    if sessions > 1:
        autonomous.append(f"work spans {sessions} sessions")
    if steps > 15:
        autonomous.append(f"{steps} steps (more than 15)")
    if files > 15:
        autonomous.append(f"{files} files (more than 15)")
    if components >= 4:
        autonomous.append(f"{components} components or systems")

    deep = []
    if unknowns >= 2:
        deep.append(f"{unknowns} unknowns")
    if risk in ("high", "irreversible"):
        deep.append(f"risk is {risk}")
    if prior_failures >= 1:
        deep.append(f"{prior_failures} earlier attempt(s) failed")
    if ambiguity == "high":
        deep.append("requirements are highly ambiguous")
    if components >= 2 and files > 5:
        deep.append(f"cross-cutting change: {components} components, {files} files")

    fast = (
        steps <= 2 and files <= 1 and components <= 1 and unknowns == 0
        and risk == "none" and ambiguity == "none" and sessions == 1 and prior_failures == 0
    )

    if autonomous:
        mode, reasons = "AUTONOMOUS", autonomous + deep
    elif deep:
        mode, reasons = "DEEP", deep
    elif fast:
        mode, reasons = "FAST", ["single clear step, at most one file, nothing unknown, reversible"]
    else:
        mode = "STANDARD"
        reasons = [f"{steps} steps, {files} file(s), {unknowns} unknown(s), risk {risk}"]

    agents: List[str] = []
    if mode == "STANDARD" and risk == "moderate":
        agents = ["reviewer"]
    elif mode == "DEEP":
        if unknowns:
            agents.append("researcher")
        if components >= 2:
            agents.append("architect")
        agents += ["reviewer", "validator"]
    elif mode == "AUTONOMOUS":
        agents = ["orchestrator", "architect", "planner", "executor", "reviewer", "validator"]

    notes: List[str] = []
    if risk == "irreversible":
        notes.append("Get explicit user approval before the irreversible step (rule 10).")
    if prior_failures >= 2:
        notes.append("Two or more failures: change the approach, do not retry unchanged (rule 7).")
    if ambiguity != "none" and mode in ("FAST", "STANDARD"):
        notes.append("State your assumption in one line; ask only if a wrong guess is costly (rule 4).")

    return {
        "mode": mode,
        "reasons": reasons,
        "required_artifacts": ARTIFACTS[mode],
        "suggested_agents": agents,
        "read": MODE_FILE[mode],
        "notes": notes,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--steps", type=int, default=1, help="distinct steps you expect (default 1)")
    parser.add_argument("--files", type=int, default=1, help="files to create or change (default 1)")
    parser.add_argument("--components", type=int, default=1, help="components or systems touched (default 1)")
    parser.add_argument("--unknowns", type=int, default=0, help="open questions or unknown causes (default 0)")
    parser.add_argument("--risk", choices=RISK_LEVELS, default="none", help="worst plausible consequence of a mistake")
    parser.add_argument("--sessions", type=int, default=1, help="sessions the work will span (default 1)")
    parser.add_argument("--prior-failures", type=int, default=0, help="earlier failed attempts at this task")
    parser.add_argument("--ambiguity", choices=AMBIGUITY_LEVELS, default="none", help="how unclear the requirements are")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    return parser


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: List[str] | None = None) -> int:
    utf8_stdio()
    args = build_parser().parse_args(argv)
    try:
        result = recommend(
            steps=args.steps, files=args.files, components=args.components,
            unknowns=args.unknowns, risk=args.risk, sessions=args.sessions,
            prior_failures=args.prior_failures, ambiguity=args.ambiguity,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Mode: {result['mode']}")
    print("Why: " + "; ".join(result["reasons"]))
    print("Produce: " + ", ".join(result["required_artifacts"]))
    agents = result["suggested_agents"]
    print("Agents: " + (", ".join(agents) if agents else "none"))
    print(f"Read: {result['read']}")
    for note in result["notes"]:
        print(f"Note: {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
