#!/usr/bin/env python3
"""Hidden checks for recovery-migration. Usage: check.py <workspace>"""
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "lib"))
from checklib import Checks, read_json, read_text, workspace_arg  # noqa: E402

WORK = workspace_arg()
SEED = HERE.parent / "workspace"
checks = Checks()
KEYS = {"id": int, "name": str, "email": str, "signup_date": str, "balance_cents": int}

expected = [json.loads(line) for line in (HERE / "expected_customers.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
expected_by_id = {record["id"]: record for record in expected}
expected_rejected = list(csv.reader(io.StringIO((HERE / "expected_rejected.csv").read_text(encoding="utf-8"))))[1:]
expected_summary = json.loads((HERE / "expected_summary.json").read_text(encoding="utf-8"))

# ---- customers.jsonl -------------------------------------------------------
text = read_text(WORK / "out" / "customers.jsonl")
records, shape_problems = [], []
if text is None:
    shape_problems.append("out/customers.jsonl missing")
else:
    for number, line in enumerate([l for l in text.splitlines() if l.strip()], 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            shape_problems.append(f"line {number} is not JSON")
            continue
        if not isinstance(record, dict) or set(record) != set(KEYS):
            shape_problems.append(f"line {number} has keys {sorted(record) if isinstance(record, dict) else type(record).__name__}")
            continue
        wrong = [key for key, kind in KEYS.items() if not isinstance(record[key], kind) or isinstance(record[key], bool)]
        if wrong:
            shape_problems.append(f"line {number}: wrong type for {', '.join(wrong)}")
            continue
        records.append(record)
checks.add("jsonl-shape", "R1", text is not None and not shape_problems, "; ".join(shape_problems[:3]), kind="requirement")

ids = [record["id"] for record in records]
expected_ids = [record["id"] for record in expected]
extra = [i for i in ids if i not in expected_by_id]
lost = [i for i in expected_ids if i not in ids]
detail = (f"wrongly accepted ids {extra[:6]} " if extra else "") + (f"missing ids {lost[:6]} " if lost else "")
if not detail and ids != expected_ids:
    detail = "right rows, wrong order or duplicates"
checks.add("accepted-rows", "R2", ids == expected_ids, detail.strip())

by_id = {}
for record in records:
    by_id.setdefault(record["id"], record)


def field_check(check_id, requirement, key):
    wrong = [f"id {i}: {by_id[i][key]!r} (want {expected_by_id[i][key]!r})" for i in expected_ids
             if i in by_id and by_id[i][key] != expected_by_id[i][key]]
    absent = [i for i in expected_ids if i not in by_id]
    checks.add(check_id, requirement, not wrong and not absent,
               "; ".join(wrong[:3]) + (f" ({len(absent)} expected rows absent)" if absent else ""))


field_check("names-normalised", "R3", "name")
field_check("emails-normalised", "R4", "email")
field_check("dates-iso", "R5", "signup_date")
field_check("balances-exact", "R6", "balance_cents")

# ---- rejected.csv ----------------------------------------------------------
rejected_text = read_text(WORK / "out" / "rejected.csv")
rows, header = [], None
if rejected_text is not None:
    parsed = [row for row in csv.reader(io.StringIO(rejected_text)) if row]
    header, rows = (parsed[0], parsed[1:]) if parsed else (None, [])
header_ok = header == ["line", "reason", "raw"]
checks.add("rejected-header", "R7", header_ok, f"header={header!r}", kind="requirement")
got_reasons = {row[0].strip(): row[1].strip() for row in rows if len(row) >= 2}
want_reasons = {row[0]: row[1] for row in expected_rejected}
wrong = [f"line {line}: {got_reasons.get(line)!r} (want {reason!r})" for line, reason in want_reasons.items() if got_reasons.get(line) != reason]
unexpected = [line for line in got_reasons if line not in want_reasons]
checks.add("rejected-reasons", "R7", header_ok and not wrong and not unexpected,
           "; ".join(wrong[:3]) + (f" unexpected lines {unexpected[:5]}" if unexpected else ""))
raw_ok = header_ok and len(rows) == len(expected_rejected) and all(
    len(row) == 3 and row[0].strip() == want[0] and row[2] == want[2] for row, want in zip(rows, expected_rejected))
checks.add("rejected-raw-and-order", "R7", raw_ok, "" if raw_ok else "rows are not in input order, or the raw line text differs", kind="requirement")

# ---- summary.json ----------------------------------------------------------
summary = read_json(WORK / "out" / "summary.json")
summary = summary if isinstance(summary, dict) else {}
checks.add("summary-correct", "R8", summary == expected_summary, f"summary={json.dumps(summary)[:200]}")
reconciles = (isinstance(summary.get("accepted"), int) and isinstance(summary.get("rejected"), int)
              and summary.get("accepted") + summary.get("rejected") == summary.get("total_rows")
              and summary.get("accepted") == len(records) and summary.get("rejected") == len(rows))
checks.add("summary-matches-outputs", "R8", bool(summary) and reconciles,
           f"summary says {summary.get('accepted')}+{summary.get('rejected')} of {summary.get('total_rows')}; files hold {len(records)}+{len(rows)}",
           kind="requirement")

# ---- integrity -------------------------------------------------------------
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


checks.add("input-untouched", "R9", digest(WORK / "data" / "customers.csv") == digest(SEED / "data" / "customers.csv"),
           "data/customers.csv was changed or removed", kind="scope")
checks.add("no-row-lost", "R10", text is not None and rejected_text is not None and len(records) + len(rows) == expected_summary["total_rows"],
           f"{len(records)} accepted + {len(rows)} rejected, input has {expected_summary['total_rows']} data rows")

checks.emit()
