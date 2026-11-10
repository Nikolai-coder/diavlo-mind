# notes — a command-line note keeper

A single file, `notes.py`, using only the Python standard library. Notes are stored in `notes.json` in the current working directory. Tests live in `test_notes.py` (`unittest`) and run with `python -m unittest test_notes -v`.

A note has an integer `id`, a `text` and a list of `tags`.

## M1 — add and list

- `python notes.py add "TEXT" [--tag TAG]...` stores a note and prints `Added note <id>`. Ids are integers starting at 1 and increasing by 1.
- `python notes.py list` prints one line per note, ordered by id: `<id>`, a TAB, the text, a TAB, then the note's tags sorted alphabetically and joined by commas. A note without tags still has the second TAB, followed by nothing.
- With no notes, `list` prints nothing.

## M2 — delete

- `python notes.py delete ID` removes the note and prints `Deleted note <id>`.
- If no note has that id, it prints `Error: note <id> not found` to standard error and exits with code 1.
- Ids are never reused: after deleting the newest note, the next `add` gets a new, higher id.

## M3 — search and tag filter

- `python notes.py search QUERY` prints, in the same format as `list`, the notes whose text contains QUERY, ignoring case.
- `python notes.py list --tag TAG` prints only the notes that have exactly that tag (case-sensitive).

## M4 — export

- `python notes.py export --format md` prints `# Notes`, an empty line, then one line per note ordered by id: `- [<id>] <text>`, followed by ` (tags: a, b)` with the tags sorted alphabetically when the note has tags.
- `python notes.py export --format json` prints a JSON array of objects with exactly the keys `id`, `text` and `tags` (tags sorted alphabetically), ordered by id.
- `--output FILE` writes the export to FILE instead of standard output and prints `Exported <n> notes to <FILE>`.
- Any other `--format` value is rejected by the argument parser (exit code 2).

## Always

- A missing `notes.json` means there are no notes; it is not an error.
- If `notes.json` exists but is not valid JSON, every command prints `Error: notes.json is corrupted` to standard error, exits with code 1 and leaves the file untouched.
- Successful commands exit with code 0.
