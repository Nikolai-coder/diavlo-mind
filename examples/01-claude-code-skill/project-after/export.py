"""Print orders from a CSV file, optionally filtered."""
import argparse
import csv
import sys
from datetime import datetime


def load(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_since(value):
    """Parse a YYYY-MM-DD string for --since, or reject it for argparse."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date {value!r}, expected YYYY-MM-DD")


def select(rows, min_amount=None, since=None):
    """Return the rows that pass the filters, in input order.

    since: a date; rows dated before it are left out, rows on it are kept.
    """
    out = []
    for row in rows:
        if min_amount is not None and float(row["amount"]) < min_amount:
            continue
        if since is not None and _row_date(row) < since:
            continue
        out.append(row)
    return out


def _row_date(row):
    return datetime.strptime(row["date"], "%Y-%m-%d").date()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print orders from a CSV file.")
    parser.add_argument("path")
    parser.add_argument("--min-amount", type=float, help="leave out orders below this amount")
    parser.add_argument(
        "--since",
        type=parse_since,
        metavar="YYYY-MM-DD",
        help="leave out orders dated before this day (orders on this day are kept)",
    )
    args = parser.parse_args(argv)
    for row in select(load(args.path), args.min_amount, args.since):
        print(f"{row['date']}  {row['customer']:<10}  {float(row['amount']):>8.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
