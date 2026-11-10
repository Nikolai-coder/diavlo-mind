"""Build the text report from parsed log records."""
from collections import Counter

LEVELS = ("ERROR", "WARN", "INFO", "DEBUG")


def build_report(records, malformed):
    """Return the report as a single string without a trailing newline."""
    levels = Counter(record["level"] for record in records)
    errors = Counter(record["service"] for record in records if record["level"] == "ERROR")
    lines = [
        "Log summary",
        f"Total: {len(records)} records, {malformed} malformed",
        "By level: " + " ".join(f"{level}={levels.get(level, 0)}" for level in LEVELS),
        "Top services by errors:",
    ]
    ranked = sorted(errors.items(), key=lambda item: (-item[1], item[0]))[:3]
    if ranked:
        lines += [f"{rank}. {service} ({count})" for rank, (service, count) in enumerate(ranked, 1)]
    else:
        lines.append("(none)")
    stamps = [record["ts"] for record in records]
    lines.append(f"First: {min(stamps) if stamps else '-'}")
    lines.append(f"Last: {max(stamps) if stamps else '-'}")
    return "\n".join(lines)
