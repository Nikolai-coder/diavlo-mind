#!/usr/bin/env python3
"""Create, validate and render DIAVLO MIND task and result packets.

    dm_packet.py new task --id T7 --role executor --objective "..." > packet.json
    dm_packet.py new result --id T7 --role executor
    dm_packet.py validate packet.json [more.json ...]
    dm_packet.py render packet.json          # text form to paste into a prompt

Field rules: workflows/protocols/handoff.md. Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dm_schema  # noqa: E402

SCHEMAS = {"task": "task-packet.schema.json", "result": "result-packet.schema.json"}


def new_task(packet_id: str, role: str, objective: str, mode: str) -> dict:
    return {
        "type": "task",
        "id": packet_id,
        "role": role,
        "mode": mode,
        "objective": objective,
        "context": [],
        "requirements": [{"id": "R1", "text": "<requirement text copied from the ledger>"}],
        "constraints": {"may_write": [], "read_only": ["everything else"], "other": []},
        "inputs": [],
        "deliverable": "<what to hand back, in what form>",
        "acceptance": ["<check that defines done>"],
        "escalate_if": [],
    }


def new_result(packet_id: str, role: str) -> dict:
    return {
        "type": "result",
        "id": packet_id,
        "role": role,
        "status": "PARTIAL",
        "summary": "<up to five lines - outcome first>",
        "deliverables": [],
        "evidence": [{"requirement": "R1", "status": "not_verified", "level": "UNKNOWN", "proof": "<command -> result>"}],
        "changes": [],
        "issues": [],
        "assumptions": [],
        "open_questions": [],
        "next": "<recommended next action>",
    }


def check(packet: dict) -> List[str]:
    """Schema errors plus the rules a schema cannot express."""
    kind = packet.get("type") if isinstance(packet, dict) else None
    if kind not in SCHEMAS:
        return ["$: field 'type' must be 'task' or 'result'"]
    errors = dm_schema.validate(packet, dm_schema.load_schema(SCHEMAS[kind]))
    if errors:
        return errors

    if kind == "task":
        writes = packet.get("constraints", {}).get("may_write", [])
        if packet["role"] in ("executor", "optimizer") and not writes:
            errors.append("$.constraints.may_write: executors and optimizers need explicit writable paths")
        if packet["role"] in ("reviewer", "validator", "researcher") and writes:
            errors.append(f"$.constraints.may_write: a {packet['role']} does not modify the work")
        ids = [req["id"] for req in packet["requirements"]]
        if len(ids) != len(set(ids)):
            errors.append("$.requirements: duplicate requirement ids")
    else:
        unmet = [e for e in packet["evidence"] if e["status"] != "met"]
        unproven = [e for e in packet["evidence"] if e["status"] == "met" and not e.get("proof")]
        blockers = [i for i in packet.get("issues", []) if i["severity"] == "blocker"]
        if packet["status"] == "DONE":
            if not packet["evidence"]:
                errors.append("$.evidence: status DONE needs at least one evidence line")
            if unmet:
                errors.append("$.status: DONE is not allowed while a requirement is unmet or not verified")
            if unproven:
                errors.append("$.evidence: every 'met' line needs a proof (rule 6: prove, don't claim)")
            if any(e.get("level") in ("ASSUMED", "UNKNOWN") for e in packet["evidence"]):
                errors.append("$.evidence: DONE cannot rest on ASSUMED or UNKNOWN evidence")
            if blockers:
                errors.append("$.issues: DONE is not allowed with an open blocker")
        if packet["status"] == "BLOCKED" and not packet.get("open_questions"):
            errors.append("$.open_questions: BLOCKED must say what is needed")
    return errors


def _lines(title: str, values: List[str]) -> List[str]:
    if not values:
        return [f"{title}: none"]
    return [f"{title}:"] + [f"  - {value}" for value in values]


def render(packet: dict) -> str:
    if packet["type"] == "task":
        constraints = packet.get("constraints", {})
        limits = [f"may write: {', '.join(constraints.get('may_write', [])) or 'nothing'}"]
        if constraints.get("read_only"):
            limits.append(f"read-only: {', '.join(constraints['read_only'])}")
        limits += constraints.get("other", [])
        out = ["TASK PACKET", f"id: {packet['id']}", f"role: {packet['role']}"]
        if packet.get("mode"):
            out.append(f"mode: {packet['mode']}")
        out.append(f"objective: {packet['objective']}")
        out += _lines("context", packet.get("context", []))
        out += _lines("requirements", [f"{r['id']}: {r['text']}" for r in packet["requirements"]])
        out += _lines("constraints", limits)
        out += _lines("inputs", packet.get("inputs", []))
        out.append(f"deliverable: {packet['deliverable']}")
        out += _lines("acceptance", packet["acceptance"])
        out += _lines("escalate_if", packet.get("escalate_if", []))
        if packet.get("budget"):
            out.append(f"budget: {packet['budget']}")
        out += ["", "Return a RESULT PACKET: status, summary, deliverables, evidence per requirement,",
                "changes, issues, assumptions, open_questions, next."]
        return "\n".join(out) + "\n"

    evidence = []
    for item in packet["evidence"]:
        parts = [item["status"]]
        if item.get("level"):
            parts.append(item["level"])
        if item.get("proof"):
            parts.append(item["proof"])
        evidence.append(f"{item['requirement']}: " + " — ".join(parts))
    issues = [
        " — ".join(p for p in (i["severity"], i.get("where"), i["finding"], i.get("suggestion")) if p)
        for i in packet.get("issues", [])
    ]
    out = ["RESULT PACKET", f"id: {packet['id']}", f"role: {packet['role']}",
           f"status: {packet['status']}", f"summary: {packet['summary']}"]
    out += _lines("deliverables", packet.get("deliverables", []))
    out += _lines("evidence", evidence)
    out += _lines("changes", [f"{c['path']} ({c['action']})" for c in packet.get("changes", [])])
    out += _lines("issues", issues)
    out += _lines("assumptions", packet.get("assumptions", []))
    out += _lines("open_questions", packet.get("open_questions", []))
    out.append(f"next: {packet.get('next') or 'none'}")
    return "\n".join(out) + "\n"


def read_packet(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: {path} is not valid JSON: {exc}")


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: Optional[List[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="DIAVLO MIND packet helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="print a packet template")
    p.add_argument("kind", choices=["task", "result"])
    p.add_argument("--id", required=True)
    p.add_argument("--role", required=True,
                   choices=["architect", "planner", "executor", "researcher", "reviewer", "validator", "optimizer", "orchestrator"])
    p.add_argument("--objective", default="<one sentence - the outcome, not the activity>")
    p.add_argument("--mode", default="STANDARD", type=str.upper, choices=["FAST", "STANDARD", "DEEP", "AUTONOMOUS"])
    p.add_argument("-o", "--output", help="write to this file instead of stdout")

    p = sub.add_parser("validate", help="check one or more packets")
    p.add_argument("files", nargs="+")

    p = sub.add_parser("render", help="print the text form of a packet")
    p.add_argument("file")

    args = parser.parse_args(argv)

    if args.command == "new":
        packet = new_task(args.id, args.role, args.objective, args.mode) if args.kind == "task" else new_result(args.id, args.role)
        text = json.dumps(packet, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"wrote {args.output}")
        else:
            sys.stdout.write(text)
        return 0

    if args.command == "validate":
        failed = 0
        for path in args.files:
            errors = check(read_packet(path))
            if errors:
                failed += 1
                print(f"{path}: INVALID")
                for line in errors:
                    print(f"  {line}")
            else:
                print(f"{path}: valid")
        return 1 if failed else 0

    packet = read_packet(args.file)
    errors = check(packet)
    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        return 1
    sys.stdout.write(render(packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
