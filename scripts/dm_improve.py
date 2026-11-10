#!/usr/bin/env python3
"""Evidence-driven improvement log for DIAVLO MIND.

Implements the bookkeeping of workflows/protocols/self-improvement.md:

    dm_improve.py record --task T --model M --arm A --observed "..." --expected "..." [--evidence PATH]
    dm_improve.py classify --id F1 --category inadequate_instructions --hypothesis "..." --change "files"
    dm_improve.py decide --id F1 --decision accepted|rejected --note "numbers and reason" \
                         [--baseline RUN_DIR --candidate RUN_DIR]
    dm_improve.py list
    dm_improve.py lock-status
    dm_improve.py approve-core-change --reason "evidence and decision"

Records live in evaluation/improvement/failures.jsonl (machine-readable) and
evaluation/improvement/improvement-log.md (human-readable, append-only).
Nothing here changes a model's weights: it tracks changes to instructions and
the measurements that justify them. Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "evaluation" / "improvement"
RECORDS = FOLDER / "failures.jsonl"
LOG = FOLDER / "improvement-log.md"
LOCK = FOLDER / "core-rules.lock.json"
CATEGORIES = ["missing_information", "inadequate_instructions", "insufficient_tools", "model_limitation"]
RULES_RE = re.compile(r"<!-- dm:core-rules:start -->(.*?)<!-- dm:core-rules:end -->", re.S)


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_records() -> List[dict]:
    if not RECORDS.is_file():
        return []
    return [json.loads(line) for line in RECORDS.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_records(records: List[dict]) -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    RECORDS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")


def append_log(text: str) -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    existing = LOG.read_text(encoding="utf-8") if LOG.is_file() else "# Improvement log\n"
    LOG.write_text(existing.rstrip("\n") + "\n\n" + text.rstrip("\n") + "\n", encoding="utf-8")


def find(records: List[dict], record_id: str) -> dict:
    for record in records:
        if record["id"] == record_id:
            return record
    raise SystemExit(f"error: unknown failure id {record_id}")


def core_rules_hash() -> str:
    match = RULES_RE.search((ROOT / "SKILL.md").read_text(encoding="utf-8"))
    if not match:
        raise SystemExit("error: core rules block not found in SKILL.md")
    return hashlib.sha256(match.group(1).strip().replace("\r\n", "\n").encode("utf-8")).hexdigest()


def run_summary(path: Optional[str]) -> Optional[dict]:
    """Headline numbers of a benchmark run directory, if it has a summary."""
    if not path:
        return None
    summary = Path(path) / "summary.json"
    if not summary.is_file():
        raise SystemExit(f"error: {summary} not found - run evaluation/score.py on that run first")
    return json.loads(summary.read_text(encoding="utf-8"))


def cmd_record(args: argparse.Namespace) -> int:
    records = load_records()
    record = {
        "id": f"F{len(records) + 1}", "date": today(), "task": args.task, "model": args.model, "arm": args.arm,
        "observed": args.observed, "expected": args.expected, "evidence": args.evidence or "",
        "category": args.category or "", "hypothesis": "", "change": "", "decision": "open", "note": "",
    }
    records.append(record)
    save_records(records)
    print(record["id"])
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    records = load_records()
    record = find(records, args.id)
    record["category"] = args.category
    record["hypothesis"] = args.hypothesis or record["hypothesis"]
    record["change"] = args.change or record["change"]
    save_records(records)
    print(f"{record['id']} classified as {record['category']}")
    if record["category"] in ("insufficient_tools", "model_limitation"):
        print("note: more instructions will not fix this category - change the tools or route the unit to a stronger model")
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    records = load_records()
    record = find(records, args.id)
    if not record["category"]:
        raise SystemExit("error: classify the failure before deciding on a change")
    baseline, candidate = run_summary(args.baseline), run_summary(args.candidate)
    if args.decision == "accepted" and not (baseline and candidate):
        raise SystemExit("error: accepting a change needs --baseline and --candidate benchmark runs as evidence")
    numbers = ""
    if baseline and candidate:
        def rate(summary: dict) -> float:
            return float(summary.get("overall", {}).get("success_rate", 0.0))
        numbers = f"success rate {rate(baseline):.2f} -> {rate(candidate):.2f}"
        if args.decision == "accepted" and rate(candidate) < rate(baseline):
            raise SystemExit(f"error: refusing to accept a change that lowers overall success ({numbers})")
    record.update({"decision": args.decision, "note": args.note, "decided": today(),
                   "baseline": args.baseline or "", "candidate": args.candidate or "", "numbers": numbers})
    save_records(records)
    append_log("\n".join([
        f"## {record['id']} — {args.decision} ({today()})",
        f"- **Task / model / arm:** {record['task']} / {record['model']} / {record['arm']}",
        f"- **Observed:** {record['observed']}",
        f"- **Expected:** {record['expected']}",
        f"- **Category:** {record['category']}",
        f"- **Hypothesis:** {record['hypothesis'] or '—'}",
        f"- **Change:** {record['change'] or '—'}",
        f"- **Runs compared:** {args.baseline or '—'} vs {args.candidate or '—'}" + (f" ({numbers})" if numbers else ""),
        f"- **Decision:** {args.decision} — {args.note}",
    ]))
    print(f"{record['id']} {args.decision}; logged in {LOG.relative_to(ROOT).as_posix()}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    records = load_records()
    if not records:
        print("no failures recorded")
    for record in records:
        print(f"{record['id']}\t{record['decision']}\t{record['category'] or 'unclassified'}\t{record['task']}\t{record['observed'][:70]}")
    return 0


def cmd_lock_status(args: argparse.Namespace) -> int:
    actual = core_rules_hash()
    if not LOCK.is_file():
        print(f"no lock file; current hash {actual}")
        return 1
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    if lock.get("sha256") == actual:
        print(f"core rules match the lock (approved {lock.get('approved')}, version {lock.get('version')})")
        return 0
    print("core rules DIFFER from the lock - an approval with a reason is required")
    print(f"  locked:  {lock.get('sha256')}\n  current: {actual}")
    return 1


def cmd_approve(args: argparse.Namespace) -> int:
    if len(args.reason.strip()) < 20:
        raise SystemExit("error: --reason must explain the evidence and the decision (at least 20 characters)")
    actual = core_rules_hash()
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    previous = json.loads(LOCK.read_text(encoding="utf-8")).get("sha256") if LOCK.is_file() else None
    if previous == actual and not args.force:
        print("core rules already match the lock; nothing to approve")
        return 0
    FOLDER.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps({"sha256": actual, "version": version, "approved": today(), "reason": args.reason}, indent=2) + "\n",
                    encoding="utf-8")
    append_log("\n".join([
        f"## Core rules approved ({today()}, version {version})",
        f"- **Previous fingerprint:** {previous or 'none (first lock)'}",
        f"- **New fingerprint:** {actual}",
        f"- **Reason:** {args.reason}",
    ]))
    print(f"lock updated to {actual[:12]}…; reason logged")
    print("remember: bump VERSION (major for a change to the ten rules) and add a CHANGELOG entry")
    return 0


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="DIAVLO MIND improvement log")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("record", help="record an observed failure")
    for flag in ("--task", "--model", "--arm", "--observed", "--expected"):
        p.add_argument(flag, required=True)
    p.add_argument("--evidence")
    p.add_argument("--category", choices=CATEGORIES)
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("classify", help="set the cause category and the proposed change")
    p.add_argument("--id", required=True)
    p.add_argument("--category", required=True, choices=CATEGORIES)
    p.add_argument("--hypothesis")
    p.add_argument("--change")
    p.set_defaults(func=cmd_classify)

    p = sub.add_parser("decide", help="accept or reject the change, with evidence")
    p.add_argument("--id", required=True)
    p.add_argument("--decision", required=True, choices=["accepted", "rejected"])
    p.add_argument("--note", required=True)
    p.add_argument("--baseline")
    p.add_argument("--candidate")
    p.set_defaults(func=cmd_decide)

    p = sub.add_parser("list", help="list recorded failures")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("lock-status", help="compare the ten rules with their approved fingerprint")
    p.set_defaults(func=cmd_lock_status)

    p = sub.add_parser("approve-core-change", help="record an approved change to the ten rules")
    p.add_argument("--reason", required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_approve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
