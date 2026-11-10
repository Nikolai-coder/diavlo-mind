"""Print orders from a CSV file, optionally filtered."""
import argparse
import csv
import sys


def load(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def select(rows, min_amount=None):
    """Return the rows that pass the filters, in input order."""
    out = []
    for row in rows:
        if min_amount is not None and float(row["amount"]) < min_amount:
            continue
        out.append(row)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print orders from a CSV file.")
    parser.add_argument("path")
    parser.add_argument("--min-amount", type=float, help="leave out orders below this amount")
    args = parser.parse_args(argv)
    for row in select(load(args.path), args.min_amount):
        print(f"{row['date']}  {row['customer']:<10}  {float(row['amount']):>8.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
