# Brief: build `logreport.py`

## Objective
Deliver one file, `logreport.py`, with one function that turns parsed log records into a text report. Another developer is building the parser that produces the records, so the record format below is a contract: rely on it exactly.

## Deliverable
Exactly one file in this directory: `logreport.py`. Python standard library only. No other files.

## Function

```python
def build_report(records: list[dict], malformed: int) -> str: ...
```

It returns the report as one string. Lines are joined with `\n`. There is no trailing newline.

## Record format (the contract)
Each record is a `dict` with exactly these four keys, all with `str` values:

| Key | Value | Example |
|---|---|---|
| `"ts"` | timestamp, always of the form `YYYY-MM-DDTHH:MM:SSZ` | `"2026-03-01T12:00:05Z"` |
| `"level"` | one of `"DEBUG"`, `"INFO"`, `"WARN"`, `"ERROR"` | `"ERROR"` |
| `"service"` | service name | `"billing-api"` |
| `"message"` | free text | `"card declined"` |

`malformed` is a non-negative integer supplied by the caller.

## Report format
```
Log summary
Total: 5 records, 1 malformed
By level: ERROR=2 WARN=1 INFO=2 DEBUG=0
Top services by errors:
1. billing-api (2)
First: 2026-03-01T12:00:05Z
Last: 2026-03-01T12:09:41Z
```

Rules:

- `Total:` always uses the words `records` and `malformed`, also for 0 and 1.
- `By level:` always lists the four levels in the order `ERROR`, `WARN`, `INFO`, `DEBUG`, including those with a count of 0.
- After `Top services by errors:` come at most three numbered lines, one per service that has at least one `ERROR` record: `<rank>. <service> (<number of ERROR records>)`. Order by error count, highest first; equal counts alphabetically by service name. If no record has level `ERROR`, the heading is followed by the single line `(none)`.
- `First:` and `Last:` show the smallest and the largest `ts` among the records (the format sorts correctly as text). With no records they are `First: -` and `Last: -`.

## Acceptance checks
```python
records = [
    {"ts": "2026-03-01T12:00:05Z", "level": "ERROR", "service": "billing-api", "message": "a"},
    {"ts": "2026-03-01T12:03:00Z", "level": "INFO", "service": "auth", "message": "b"},
    {"ts": "2026-03-01T12:09:41Z", "level": "ERROR", "service": "billing-api", "message": "c"},
    {"ts": "2026-03-01T12:04:00Z", "level": "WARN", "service": "queue-2", "message": "d"},
    {"ts": "2026-03-01T12:05:00Z", "level": "INFO", "service": "auth", "message": "e"},
]
assert build_report(records, 1) == (
    "Log summary\nTotal: 5 records, 1 malformed\nBy level: ERROR=2 WARN=1 INFO=2 DEBUG=0\n"
    "Top services by errors:\n1. billing-api (2)\nFirst: 2026-03-01T12:00:05Z\nLast: 2026-03-01T12:09:41Z"
)
assert build_report([], 0) == (
    "Log summary\nTotal: 0 records, 0 malformed\nBy level: ERROR=0 WARN=0 INFO=0 DEBUG=0\n"
    "Top services by errors:\n(none)\nFirst: -\nLast: -"
)
```

## Stop and report instead of guessing if
Anything above seems contradictory. Do not rename keys or reorder the report lines.
