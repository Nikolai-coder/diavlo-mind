"""Print orders from a CSV file, optionally filtered."""
import argparse
import csv
import datetime
import re
import sys


def parse_date(text):
    """argparse type: strict YYYY-MM-DD -> datetime.date."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise argparse.ArgumentTypeError(f"invalid date {text!r}: expected YYYY-MM-DD")
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date {text!r}: expected YYYY-MM-DD")


def load(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def select(rows, min_amount=None, since=None):
    """Return the rows that pass the filters, in input order."""
    out = []
    for row in rows:
        if min_amount is not None and float(row["amount"]) < min_amount:
            continue
        if since is not None and datetime.date.fromisoformat(row["date"].strip()) < since:
            continue
        out.append(row)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print orders from a CSV file.")
    parser.add_argument("path")
    parser.add_argument("--min-amount", type=float, help="leave out orders below this amount")
    parser.add_argument("--since", type=parse_date, metavar="YYYY-MM-DD", help="leave out orders dated before this day")
    args = parser.parse_args(argv)
    for row in select(load(args.path), args.min_amount, args.since):
        print(f"{row['date']}  {row['customer']:<10}  {float(row['amount']):>8.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
