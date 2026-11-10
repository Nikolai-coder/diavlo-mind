#!/usr/bin/env python3
"""Minimal JSON Schema validator used by the DIAVLO MIND scripts.

Supports the subset of JSON Schema (draft 2020-12) used by the files in
memory/schemas/: type, const, enum, required, properties,
additionalProperties (boolean), items, minItems, minLength, pattern, minimum.

It exists so the scripts run with the Python standard library alone. The
schemas themselves are standard and can be checked with any full validator.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, List

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "memory" / "schemas"

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def load_schema(name: str) -> dict:
    """Load a schema by file name from memory/schemas/."""
    path = SCHEMA_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[expected])


def validate(instance: Any, schema: dict, path: str = "$") -> List[str]:
    """Return a list of human-readable errors. An empty list means valid."""
    errors: List[str] = []

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must be {schema['const']!r}, got {instance!r}")
        return errors
    if "enum" in schema and instance not in schema["enum"]:
        allowed = ", ".join(repr(v) for v in schema["enum"])
        errors.append(f"{path}: {instance!r} is not one of {allowed}")
        return errors

    expected = schema.get("type")
    if expected and not _type_ok(instance, expected):
        errors.append(f"{path}: expected {expected}, got {type(instance).__name__}")
        return errors

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match {schema['pattern']}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} is below the minimum {schema['minimum']}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(validate(item, item_schema, f"{path}[{index}]"))

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required field '{key}'")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                errors.extend(validate(value, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unknown field '{key}'")

    return errors


def utf8_stdio() -> None:
    """Write UTF-8 regardless of the platform's default encoding (Windows pipes use a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: List[str]) -> int:
    utf8_stdio()
    if len(argv) != 3:
        print("usage: dm_schema.py <schema-file-name> <json-file>", file=sys.stderr)
        return 2
    try:
        schema = load_schema(argv[1])
        instance = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    errors = validate(instance, schema)
    for line in errors:
        print(line)
    print("valid" if not errors else f"{len(errors)} error(s)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
