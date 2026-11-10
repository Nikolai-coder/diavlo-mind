# Handoff

## Status

| Milestone | State | How to confirm |
|---|---|---|
| M1 add / list | done | `python -m unittest test_notes -v` |
| M2 delete | done | same |
| M3 search / list --tag | done | same |
| M4 export | done | same |

## Decisions

- `notes.json` stores `{"next_id": n, "notes": [...]}` so ids are never reused after a delete.
- Tags are stored sorted and de-duplicated.
- Every command loads through `load()`, which raises `CorruptedStore`; `main()` turns that into the error message and exit code 1 without writing.

## How to run

```
python notes.py add "text" --tag a
python notes.py list
python -m unittest test_notes -v
```
