"""Migrate the legacy customer export according to RULES.md.

Usage: migrate.py INPUT OUT_DIR

Writes OUT_DIR/customers.jsonl, OUT_DIR/rejected.csv and OUT_DIR/summary.json.
"""
import csv
import io
import json
import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

BALANCE = re.compile(r"-?(\d{1,3}(,\d{3})+|\d+)(\.\d{1,2})?")
REASONS = ["wrong_column_count", "missing_id", "invalid_id", "duplicate_id", "invalid_email", "invalid_date", "invalid_balance"]


def parse_date(text):
    for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text.strip(), pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def valid_email(email):
    if email.count("@") != 1:
        return False
    local, domain = email.split("@")
    return bool(local) and "." in domain and all(domain.split("."))


def convert(fields, seen):
    """Return (record, None) or (None, reason)."""
    if len(fields) != 5:
        return None, "wrong_column_count"
    raw_id, name, email, date, balance = fields
    raw_id = raw_id.strip()
    if not raw_id:
        return None, "missing_id"
    if not raw_id.isdigit() or int(raw_id) <= 0:
        return None, "invalid_id"
    if int(raw_id) in seen:
        return None, "duplicate_id"
    email = email.strip().lower()
    if not valid_email(email):
        return None, "invalid_email"
    iso = parse_date(date)
    if iso is None:
        return None, "invalid_date"
    balance = balance.strip()
    if not BALANCE.fullmatch(balance):
        return None, "invalid_balance"
    cents = int(Decimal(balance.replace(",", "")) * 100)
    return {"id": int(raw_id), "name": " ".join(name.split()), "email": email,
            "signup_date": iso, "balance_cents": cents}, None


def migrate(source, out_dir):
    lines = Path(source).read_text(encoding="utf-8").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    accepted, rejected, seen = [], [], set()
    for number, line in enumerate(lines[1:], start=2):
        fields = next(csv.reader(io.StringIO(line)))
        record, reason = convert(fields, seen)
        if record:
            seen.add(record["id"])
            accepted.append(record)
        else:
            rejected.append((number, reason, line))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "customers.jsonl", "w", encoding="utf-8", newline="\n") as target:
        for record in accepted:
            target.write(json.dumps(record, ensure_ascii=False) + "\n")
    with open(out / "rejected.csv", "w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(["line", "reason", "raw"])
        writer.writerows(rejected)
    by_reason = {reason: sum(1 for _, r, _ in rejected if r == reason) for reason in REASONS}
    summary = {"total_rows": len(lines) - 1, "accepted": len(accepted), "rejected": len(rejected),
               "by_reason": {reason: count for reason, count in by_reason.items() if count}}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    if len(sys.argv) != 3:
        print("usage: migrate.py INPUT OUT_DIR", file=sys.stderr)
        sys.exit(2)
    summary = migrate(sys.argv[1], sys.argv[2])
    assert summary["accepted"] + summary["rejected"] == summary["total_rows"]
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
