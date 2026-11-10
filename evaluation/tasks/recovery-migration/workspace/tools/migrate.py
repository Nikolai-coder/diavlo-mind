"""Migrate the legacy customer export to JSON lines.

Usage: migrate.py INPUT OUTPUT
"""
import csv
import json
import sys
from datetime import datetime


def convert(row):
    return {
        "id": int(row["id"]),
        "name": row["name"].strip(),
        "email": row["email"],
        "signup_date": datetime.strptime(row["signup_date"], "%Y-%m-%d").strftime("%Y-%m-%d"),
        "balance_cents": int(float(row["balance"]) * 100),
    }


def main():
    if len(sys.argv) != 3:
        print("usage: migrate.py INPUT OUTPUT")
        sys.exit(2)
    with open(sys.argv[1], newline="", encoding="utf-8") as source, open(sys.argv[2], "w", encoding="utf-8") as target:
        for row in csv.DictReader(source):
            target.write(json.dumps(convert(row)) + "\n")
    print("migration complete")


if __name__ == "__main__":
    main()
