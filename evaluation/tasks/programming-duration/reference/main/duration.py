"""Parse and format compact durations such as ``1h30m``."""
import re

_UNITS = (("w", 604800), ("d", 86400), ("h", 3600), ("m", 60), ("s", 1))
_SECONDS = dict(_UNITS)
_ORDER = [unit for unit, _ in _UNITS]
_COMPONENT = re.compile(r"([0-9]+)([wdhms])", re.IGNORECASE)
_INTEGER = re.compile(r"[0-9]+")


def parse_duration(text):
    """Return the number of seconds described by ``text``."""
    if not isinstance(text, str):
        raise TypeError(f"duration must be a str, not {type(text).__name__}")
    stripped = text.strip()
    if not stripped:
        raise ValueError(f"empty duration: {text!r}")
    if _INTEGER.fullmatch(stripped):
        return int(stripped)

    total = 0
    last_rank = -1
    position = 0
    while position < len(stripped):
        match = _COMPONENT.match(stripped, position)
        if not match:
            raise ValueError(f"invalid duration: {text!r}")
        rank = _ORDER.index(match.group(2).lower())
        if rank <= last_rank:
            raise ValueError(f"units repeated or out of order in duration: {text!r}")
        last_rank = rank
        total += int(match.group(1)) * _SECONDS[match.group(2).lower()]
        position = match.end()
        while position < len(stripped) and stripped[position].isspace():
            position += 1
    return total


def format_duration(seconds):
    """Return the canonical compact form of a non-negative number of seconds."""
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise TypeError(f"seconds must be an int, not {type(seconds).__name__}")
    if seconds < 0:
        raise ValueError(f"seconds must not be negative: {seconds}")
    if seconds == 0:
        return "0s"
    parts = []
    for unit, size in _UNITS:
        count, seconds = divmod(seconds, size)
        if count:
            parts.append(f"{count}{unit}")
    return "".join(parts)
