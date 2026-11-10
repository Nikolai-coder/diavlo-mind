#!/usr/bin/env python3
"""Paired comparison of two benchmark configurations.

    # two arms inside one results folder
    python evaluation/compare_runs.py evaluation/runs/<label> --arm-a baseline --arm-b diavlo-mind

    # two results folders (for example framework version 1.0.0 against a candidate change)
    python evaluation/compare_runs.py <baseline-run-dir> <candidate-run-dir>

Runs are paired by task and trial. The report gives per-task differences and an
exact two-sided sign test on requirement coverage. With few pairs the test
cannot support a conclusion, and the report says so.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load(folder: Path, arm: Optional[str]) -> Dict[Tuple[str, int], dict]:
    out: Dict[Tuple[str, int], dict] = {}
    for path in sorted(folder.rglob("result.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        if arm and result["arm"] != arm:
            continue
        out[(result["task"], result["trial"])] = result
    return out


def sign_test(wins: int, losses: int) -> Optional[float]:
    """Exact two-sided sign test on the non-tied pairs."""
    n = wins + losses
    if n == 0:
        return None
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def ratio(a: Optional[float], b: Optional[float]) -> str:
    if not a or b is None:
        return "n/a"
    return f"{b / a:.2f}x"


def compare(a: Dict[Tuple[str, int], dict], b: Dict[Tuple[str, int], dict]) -> dict:
    keys = sorted(set(a) & set(b))
    rows, wins, losses, solved_only_b, solved_only_a = [], 0, 0, 0, 0
    for key in keys:
        ra, rb = a[key], b[key]
        delta = round((rb.get("requirement_coverage") or 0) - (ra.get("requirement_coverage") or 0), 3)
        wins += delta > 0
        losses += delta < 0
        solved_only_b += bool(rb["success"]) and not ra["success"]
        solved_only_a += bool(ra["success"]) and not rb["success"]
        rows.append({
            "task": key[0], "trial": key[1],
            "success_a": ra["success"], "success_b": rb["success"],
            "coverage_a": ra.get("requirement_coverage"), "coverage_b": rb.get("requirement_coverage"), "coverage_delta": delta,
            "checks_a": f"{ra['passed']}/{ra['total']}", "checks_b": f"{rb['passed']}/{rb['total']}",
            "overclaim_a": ra.get("overclaim"), "overclaim_b": rb.get("overclaim"),
            "output_tokens_a": ra.get("output_tokens"), "output_tokens_b": rb.get("output_tokens"),
            "cost_a": ra.get("cost_usd"), "cost_b": rb.get("cost_usd"),
        })

    def rate(side: str) -> Optional[float]:
        return round(sum(1 for r in rows if r[f"success_{side}"]) / len(rows), 4) if rows else None

    def total(field: str) -> Optional[float]:
        values = [r[field] for r in rows if r[field] is not None]
        return sum(values) if values else None

    return {
        "pairs": len(rows), "only_in_a": len(set(a) - set(b)), "only_in_b": len(set(b) - set(a)),
        "success_rate_a": rate("a"), "success_rate_b": rate("b"),
        "coverage_wins_b": wins, "coverage_losses_b": losses, "coverage_ties": len(rows) - wins - losses,
        "sign_test_p": sign_test(wins, losses),
        "solved_only_by_b": solved_only_b, "solved_only_by_a": solved_only_a,
        "success_sign_test_p": sign_test(solved_only_b, solved_only_a),
        "overclaims_a": sum(1 for r in rows if r["overclaim_a"]), "overclaims_b": sum(1 for r in rows if r["overclaim_b"]),
        "output_tokens_a": total("output_tokens_a"), "output_tokens_b": total("output_tokens_b"),
        "cost_a": total("cost_a"), "cost_b": total("cost_b"),
        "rows": rows,
    }


def render(result: dict, name_a: str, name_b: str) -> str:
    def pct(value: Optional[float]) -> str:
        return "n/a" if value is None else f"{value * 100:.0f}%"

    lines = [f"# Comparison: A = {name_a}, B = {name_b}", "",
             f"{result['pairs']} paired run(s) (same task and trial)."
             + (f" Unpaired: {result['only_in_a']} only in A, {result['only_in_b']} only in B." if result["only_in_a"] or result["only_in_b"] else ""),
             "", "| | A | B |", "|---|---|---|",
             f"| Task success rate | {pct(result['success_rate_a'])} | {pct(result['success_rate_b'])} |",
             f"| Overclaims | {result['overclaims_a']} | {result['overclaims_b']} |",
             f"| Output tokens (sum) | {result['output_tokens_a'] if result['output_tokens_a'] is not None else 'n/a'} | "
             f"{result['output_tokens_b'] if result['output_tokens_b'] is not None else 'n/a'} ({ratio(result['output_tokens_a'], result['output_tokens_b'])}) |",
             f"| Cost (sum, USD) | {result['cost_a'] if result['cost_a'] is None else round(result['cost_a'], 3)} | "
             f"{result['cost_b'] if result['cost_b'] is None else round(result['cost_b'], 3)} ({ratio(result['cost_a'], result['cost_b'])}) |",
             "", f"Requirement coverage: B higher in {result['coverage_wins_b']} pair(s), lower in {result['coverage_losses_b']}, "
             f"equal in {result['coverage_ties']}."]
    def verdict(p_value: Optional[float], decided: int) -> str:
        if p_value is None:
            return "Sign test: not applicable (no pair differs)."
        if decided < 6:
            return (f"Sign test: p = {p_value:.3f} on {decided} differing pair(s). "
                    "Too few pairs to conclude anything; run more tasks or more trials.")
        reading = ("a difference this large would be unusual if the two configurations were equally good"
                   if p_value < 0.05 else "a difference this large is expected by chance alone often enough that it proves nothing")
        return f"Sign test (exact, two-sided): p = {p_value:.3f} on {decided} differing pairs; {reading}."

    lines.append(verdict(result["sign_test_p"], result["coverage_wins_b"] + result["coverage_losses_b"]))
    lines += ["", f"Task success: B solved and A did not in {result['solved_only_by_b']} pair(s); "
                  f"A solved and B did not in {result['solved_only_by_a']}.",
              verdict(result["success_sign_test_p"], result["solved_only_by_b"] + result["solved_only_by_a"])]
    lines += ["", "| Task | Trial | Success A → B | Checks A → B | Coverage A → B | Overclaim A / B | Output tokens A → B | Cost A → B |",
              "|---|---|---|---|---|---|---|---|"]
    for row in result["rows"]:
        def flag(value: object) -> str:
            return "yes" if value else "no"
        lines.append(
            f"| {row['task']} | {row['trial']} | {flag(row['success_a'])} → {flag(row['success_b'])} | {row['checks_a']} → {row['checks_b']} | "
            f"{pct(row['coverage_a'])} → {pct(row['coverage_b'])} | {flag(row['overclaim_a'])} / {flag(row['overclaim_b'])} | "
            f"{row['output_tokens_a']} → {row['output_tokens_b']} | {row['cost_a']} → {row['cost_b']} |")
    return "\n".join(lines) + "\n"


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Compare two benchmark configurations, paired by task and trial.")
    parser.add_argument("a", help="results folder for A (or the only folder when both arms live in it)")
    parser.add_argument("b", nargs="?", help="results folder for B (default: the same folder as A)")
    parser.add_argument("--arm-a", help="arm to take from A")
    parser.add_argument("--arm-b", help="arm to take from B")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", help="also write the Markdown report to this file")
    args = parser.parse_args(argv)
    folder_a, folder_b = Path(args.a), Path(args.b or args.a)
    if folder_a == folder_b and not (args.arm_a and args.arm_b):
        raise SystemExit("error: comparing within one folder needs --arm-a and --arm-b")
    runs_a, runs_b = load(folder_a, args.arm_a), load(folder_b, args.arm_b)
    if not runs_a or not runs_b:
        raise SystemExit("error: one side has no results (check the folders and arm names)")
    result = compare(runs_a, runs_b)
    if result["pairs"] == 0:
        raise SystemExit("error: no task/trial pair exists in both sides")
    name_a = f"{folder_a.name}" + (f" [{args.arm_a}]" if args.arm_a else "")
    name_b = f"{folder_b.name}" + (f" [{args.arm_b}]" if args.arm_b else "")
    text = render(result, name_a, name_b)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
