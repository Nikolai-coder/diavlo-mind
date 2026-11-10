#!/usr/bin/env python3
"""notes - a command-line note keeper. See SPEC.md."""
import argparse
import json
import sys
from pathlib import Path

STORE = Path("notes.json")


class CorruptedStore(Exception):
    pass


def load():
    """Return (notes, next_id). A missing file means no notes."""
    if not STORE.exists():
        return [], 1
    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
        notes = data["notes"]
        next_id = int(data["next_id"])
        for note in notes:
            int(note["id"]), str(note["text"]), list(note["tags"])
    except (ValueError, KeyError, TypeError) as exc:
        raise CorruptedStore() from exc
    return notes, next_id


def save(notes, next_id):
    STORE.write_text(json.dumps({"next_id": next_id, "notes": notes}, indent=2) + "\n", encoding="utf-8")


def line(note):
    return f"{note['id']}\t{note['text']}\t{','.join(sorted(note['tags']))}"


def cmd_add(args):
    notes, next_id = load()
    notes.append({"id": next_id, "text": args.text, "tags": sorted(set(args.tag or []))})
    save(notes, next_id + 1)
    print(f"Added note {next_id}")
    return 0


def cmd_list(args):
    notes, _ = load()
    for note in sorted(notes, key=lambda n: n["id"]):
        if args.tag is None or args.tag in note["tags"]:
            print(line(note))
    return 0


def cmd_delete(args):
    notes, next_id = load()
    remaining = [note for note in notes if note["id"] != args.id]
    if len(remaining) == len(notes):
        print(f"Error: note {args.id} not found", file=sys.stderr)
        return 1
    save(remaining, next_id)
    print(f"Deleted note {args.id}")
    return 0


def cmd_search(args):
    notes, _ = load()
    query = args.query.lower()
    for note in sorted(notes, key=lambda n: n["id"]):
        if query in note["text"].lower():
            print(line(note))
    return 0


def cmd_export(args):
    notes, _ = load()
    notes = sorted(notes, key=lambda n: n["id"])
    if args.format == "json":
        text = json.dumps([{"id": n["id"], "text": n["text"], "tags": sorted(n["tags"])} for n in notes], indent=2) + "\n"
    else:
        rows = ["# Notes", ""]
        for note in notes:
            tags = f" (tags: {', '.join(sorted(note['tags']))})" if note["tags"] else ""
            rows.append(f"- [{note['id']}] {note['text']}{tags}")
        text = "\n".join(rows) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Exported {len(notes)} notes to {args.output}")
    else:
        sys.stdout.write(text)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="notes.py", description="A command-line note keeper.")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="add a note")
    add.add_argument("text")
    add.add_argument("--tag", action="append")
    add.set_defaults(func=cmd_add)

    listing = sub.add_parser("list", help="list notes")
    listing.add_argument("--tag")
    listing.set_defaults(func=cmd_list)

    delete = sub.add_parser("delete", help="delete a note")
    delete.add_argument("id", type=int)
    delete.set_defaults(func=cmd_delete)

    search = sub.add_parser("search", help="search note text")
    search.add_argument("query")
    search.set_defaults(func=cmd_search)

    export = sub.add_parser("export", help="export notes")
    export.add_argument("--format", required=True, choices=["md", "json"])
    export.add_argument("--output")
    export.set_defaults(func=cmd_export)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CorruptedStore:
        print("Error: notes.json is corrupted", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
