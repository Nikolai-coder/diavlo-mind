# Brief: build `logparse.py`

## Objective
Deliver one file, `logparse.py`, containing two functions that turn service-log text into records. Another developer is building a module that consumes your records, so the names and formats below are a contract: follow them exactly.

## Deliverable
Exactly one file in this directory: `logparse.py`. Python standard library only. No other files.

## Functions

```python
def parse_log(text: str) -> list[dict]: ...
def count_malformed(text: str) -> int: ...
```

- `parse_log` returns one record per valid line, in input order.
- `count_malformed` returns the number of malformed lines.

## Record format (the contract)
Each record is a `dict` with exactly these four keys, all with `str` values:

| Key | Value |
|---|---|
| `"ts"` | the timestamp exactly as written in the line |
| `"level"` | the level |
| `"service"` | the service name |
| `"message"` | the message |

## Line format
Example of a valid line:

```
2026-03-01T12:00:05Z ERROR billing-api: card declined for order 1182
```

A valid line has, in this order:

1. a timestamp of the exact form `YYYY-MM-DDTHH:MM:SSZ` (digits, literal `T` and `Z`),
2. one space,
3. a level that is exactly `DEBUG`, `INFO`, `WARN` or `ERROR` (upper case),
4. one space,
5. a service name of lower-case letters, digits and hyphens, at least one character,
6. a colon followed by one space,
7. the message: the rest of the line with trailing whitespace removed. It must not be empty.

Lines that are empty or only whitespace are ignored: they are neither records nor malformed. Every other line that does not match is malformed.

## Acceptance checks
```python
text = (
    "2026-03-01T12:00:05Z ERROR billing-api: card declined for order 1182\n"
    "\n"
    "not a log line\n"
    "2026-03-01T12:01:00Z info billing-api: lower-case level is malformed\n"
    "2026-03-01T12:02:00Z WARN queue-2: depth 80   \n"
)
assert parse_log(text) == [
    {"ts": "2026-03-01T12:00:05Z", "level": "ERROR", "service": "billing-api", "message": "card declined for order 1182"},
    {"ts": "2026-03-01T12:02:00Z", "level": "WARN", "service": "queue-2", "message": "depth 80"},
]
assert count_malformed(text) == 2
assert parse_log("") == [] and count_malformed("") == 0
```

## Stop and report instead of guessing if
Anything above seems contradictory. Do not change the key names or add keys.
