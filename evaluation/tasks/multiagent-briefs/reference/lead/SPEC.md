# logsum — specification

`logsum` summarises service logs. It consists of two Python modules that are developed separately and used together like this:

```python
from logparse import parse_log, count_malformed
from logreport import build_report

text = open("service.log", encoding="utf-8").read()
print(build_report(parse_log(text), count_malformed(text)))
```

Only the Python standard library may be used.

## Module `logparse.py`

### Log line format

```
2026-03-01T12:00:05Z ERROR billing-api: card declined for order 1182
```

A valid line has, in order:

1. a timestamp of the exact form `YYYY-MM-DDTHH:MM:SSZ` (digits, with the literal `T` and `Z`),
2. one space,
3. a level, which is exactly one of `DEBUG`, `INFO`, `WARN`, `ERROR` (upper case),
4. one space,
5. a service name made of lower-case letters, digits and hyphens, at least one character,
6. a colon followed by one space,
7. the message: the rest of the line, with trailing whitespace removed. It must not be empty.

Lines that are empty or contain only whitespace are ignored. Every other line that does not match is *malformed*.

### Functions

- `parse_log(text: str) -> list[dict]` returns one record per valid line, in input order. A record is a `dict` with exactly these keys, all with `str` values:
  - `"ts"` — the timestamp exactly as written,
  - `"level"` — the level,
  - `"service"` — the service name,
  - `"message"` — the message.
- `count_malformed(text: str) -> int` returns the number of malformed lines.

## Module `logreport.py`

- `build_report(records: list[dict], malformed: int) -> str` takes records in the format above and returns the report as one string. Lines are joined with `\n` and there is no trailing newline.

### Report format

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

- `Total:` always uses the words `records` and `malformed`, also for the numbers 0 and 1.
- `By level:` always lists the four levels in the order `ERROR`, `WARN`, `INFO`, `DEBUG`, including levels with a count of 0.
- `Top services by errors:` is followed by at most three numbered lines, one per service that has at least one `ERROR` record: `<rank>. <service> (<number of ERROR records>)`. Services are ordered by error count, highest first; services with the same count are ordered alphabetically. If no record has level `ERROR`, the heading is followed by the single line `(none)`.
- `First:` and `Last:` show the smallest and the largest timestamp among the records. With no records both show a hyphen: `First: -` and `Last: -`.
