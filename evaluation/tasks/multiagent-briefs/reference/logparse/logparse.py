"""Parse service log lines into records."""
import re

_LINE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<level>DEBUG|INFO|WARN|ERROR) "
    r"(?P<service>[a-z0-9-]+): "
    r"(?P<message>.*)"
)


def _classify(text):
    """Yield (record or None) for every line that is not blank."""
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _LINE.fullmatch(line.rstrip())
        if match and match.group("message").strip():
            record = match.groupdict()
            record["message"] = record["message"].rstrip()
            yield record
        else:
            yield None


def parse_log(text):
    """Return one record per valid line, in input order."""
    return [record for record in _classify(text) if record is not None]


def count_malformed(text):
    """Return the number of lines that are neither blank nor valid."""
    return sum(1 for record in _classify(text) if record is None)
