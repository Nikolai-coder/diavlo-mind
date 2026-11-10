#!/usr/bin/env python3
"""Hidden checks for multiagent-briefs. Usage: check.py <assembled-workspace>

The assembled workspace holds the two briefs and the two modules, each built by
a different isolated worker. DM_WORKSPACES (set by the harness) maps workspace
names to directories so each worker's own delivery can be inspected.
"""
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "lib"))
from checklib import Checks, read_text, run_cases, visible_files, workspace_arg  # noqa: E402

WORK = workspace_arg()
checks = Checks()
fixtures = json.loads((HERE / "fixtures.json").read_text(encoding="utf-8"))
INPUTS, EXPECTED = fixtures["inputs"], fixtures["expected"]
KEYS = ["ts", "level", "service", "message"]

briefs = {name: read_text(WORK / "briefs" / f"{name}.md") or "" for name in ("logparse", "logreport")}
thin = [name for name, text in briefs.items() if len(text.strip()) < 200]
checks.add("briefs-written", "R1", not thin, "missing or under 200 characters: " + ", ".join(thin) if thin else "", kind="process")


def names_key(text, key):
    return bool(re.search(rf"""["'`]{key}["'`]""", text))


gaps = [f"{name} lacks {key!r}" for name, text in briefs.items() for key in KEYS if not names_key(text, key)]
checks.add("contract-in-both-briefs", "R2", not gaps and not thin, "; ".join(gaps[:4]), kind="process")

RECORDS = [
    {"ts": "2026-03-01T12:00:05Z", "level": "ERROR", "service": "billing-api", "message": "a"},
    {"ts": "2026-03-01T12:03:00Z", "level": "ERROR", "service": "auth", "message": "b"},
    {"ts": "2026-03-01T12:09:41Z", "level": "ERROR", "service": "billing-api", "message": "c"},
    {"ts": "2026-03-01T12:04:00Z", "level": "WARN", "service": "queue-2", "message": "d"},
    {"ts": "2026-03-01T12:05:00Z", "level": "ERROR", "service": "zeta", "message": "e"},
    {"ts": "2026-03-01T12:06:00Z", "level": "ERROR", "service": "alpha", "message": "f"},
    {"ts": "2026-03-01T11:00:00Z", "level": "DEBUG", "service": "alpha", "message": "g"},
]
REPORT = ("Log summary\nTotal: 7 records, 1 malformed\nBy level: ERROR=5 WARN=1 INFO=0 DEBUG=1\n"
          "Top services by errors:\n1. billing-api (2)\n2. alpha (1)\n3. auth (1)\nFirst: 2026-03-01T11:00:00Z\nLast: 2026-03-01T12:09:41Z")
ONE = [{"ts": "2026-01-01T00:00:00Z", "level": "INFO", "service": "solo", "message": "x"}]
ONE_REPORT = ("Log summary\nTotal: 1 records, 0 malformed\nBy level: ERROR=0 WARN=0 INFO=1 DEBUG=0\n"
              "Top services by errors:\n(none)\nFirst: 2026-01-01T00:00:00Z\nLast: 2026-01-01T00:00:00Z")

parse_cases = {f"records:{name}": f"parse_log({text!r})" for name, text in INPUTS.items()}
parse_cases.update({f"malformed:{name}": f"count_malformed({text!r})" for name, text in INPUTS.items()})
parse_cases["types"] = f"sorted({{type(v).__name__ for r in parse_log({INPUTS['normal']!r}) for v in r.values()}})"
parse = run_cases(WORK, "from logparse import parse_log, count_malformed", parse_cases)


def value(results, name):
    return results[name].get("value") if results[name].get("ok") else None


problems = []
for name in INPUTS:
    if value(parse, f"records:{name}") != EXPECTED[name]["records"]:
        problems.append(f"parse_log wrong on '{name}'" + (f": {parse[f'records:{name}'].get('error', '')}" if not parse[f"records:{name}"].get("ok") else ""))
    if value(parse, f"malformed:{name}") != EXPECTED[name]["malformed"]:
        problems.append(f"count_malformed on '{name}' = {value(parse, f'malformed:{name}')!r}, expected {EXPECTED[name]['malformed']}")
if value(parse, "types") != ["str"]:
    problems.append(f"record values are not all str: {value(parse, 'types')}")
checks.add("logparse-correct", "R3", not problems, "; ".join(problems[:3]))

report_cases = {"full": f"build_report({RECORDS!r}, 1)", "one": f"build_report({ONE!r}, 0)", "empty": "build_report([], 0)"}
report = run_cases(WORK, "from logreport import build_report", report_cases)
problems = []
for name, expected in (("full", REPORT), ("one", ONE_REPORT), ("empty", EXPECTED["empty"]["report"])):
    got = value(report, name)
    if got != expected:
        shown = report[name].get("error") if not report[name].get("ok") else repr(got)[:160]
        problems.append(f"build_report '{name}': {shown}")
checks.add("logreport-correct", "R4", not problems, "; ".join(problems[:2]))

together = "from logparse import parse_log, count_malformed\nfrom logreport import build_report"
integration = run_cases(WORK, together, {name: f"build_report(parse_log({text!r}), count_malformed({text!r}))" for name, text in INPUTS.items()})
for name in INPUTS:
    got = value(integration, name)
    shown = integration[name].get("error") if not integration[name].get("ok") else ("" if got == EXPECTED[name]["report"] else repr(got)[:200])
    checks.add(f"integration-{name.replace('_', '-')}", "R5", got == EXPECTED[name]["report"], shown or "")

# R6: each worker delivered exactly its own module
try:
    spaces = json.loads(os.environ.get("DM_WORKSPACES", "{}"))
except json.JSONDecodeError:
    spaces = {}
if spaces:
    problems = []
    for worker, module in (("logparse", "logparse.py"), ("logreport", "logreport.py")):
        folder = Path(spaces.get(worker, ""))
        files = [name for name in visible_files(folder) if name != "BRIEF.md"] if folder.is_dir() else []
        if files != [module]:
            problems.append(f"{worker} delivered {files or 'nothing'}")
    lead = Path(spaces.get("lead", ""))
    lead_extra = [name for name in visible_files(lead) if name not in ("SPEC.md", "briefs/logparse.md", "briefs/logreport.md")] if lead.is_dir() else []
    if lead_extra:
        problems.append(f"lead created {lead_extra[:4]}")
    checks.add("deliveries-in-scope", "R6", not problems, "; ".join(problems), kind="scope")
else:
    present = [(WORK / name).is_file() for name in ("logparse.py", "logreport.py")]
    checks.add("deliveries-in-scope", "R6", all(present), "worker folders not available; checked only that both modules exist", kind="scope")

checks.emit()
