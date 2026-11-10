#!/usr/bin/env python3
"""Hidden checks for programming-duration. Usage: check.py <workspace>"""
import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from checklib import Checks, raised, run, run_cases, visible_files, workspace_arg  # noqa: E402

WORK = workspace_arg()
checks = Checks()
SETUP = "from duration import parse_duration, format_duration"


def value(result):
    return result.get("value") if result.get("ok") else None


def all_equal(results, expected):
    """Every named case evaluated to its expected value."""
    wrong = [f"{name} -> {results[name].get('value', results[name].get('error'))!r}, expected {want!r}"
             for name, want in expected.items() if value(results[name]) != want or not results[name].get("ok")]
    return not wrong, "; ".join(wrong[:3])


def all_raise(results, names, exception):
    wrong = [f"{name} -> {results[name].get('value', results[name].get('error'))!r}" for name in names
             if not raised(results[name], exception)]
    return not wrong, "; ".join(wrong[:3])


parse_ok = {
    "45s": 45, "2m": 120, "1h": 3600, "1d": 86400, "1w": 604800, "1h30m": 5400, "1w2d3h4m5s": 788645, "0s": 0,
    "2d 4h": 187200, "  1h30m  ": 5400, "1h  30m": 5400,
    "1H30M": 5400, "1W": 604800, "2D4h": 187200,
    "90": 90, " 90 ": 90, "0": 0,
    "01h05m": 3900, "090": 90, "007s": 7,
    "100000h": 360000000,
}
cases = {f"p:{text}": f"parse_duration({text!r})" for text in parse_ok}
bad_value = ["", "   ", "1x", "h", "-1h", "+1h", "1.5h", "abc", "1 h", "1h30", "1m1h", "1d1d", "1s1w", "1h1h30m", "1h-30m", "h1"]
cases.update({f"bv:{text}": f"parse_duration({text!r})" for text in bad_value})
cases.update({f"msg:{text}": f"(lambda: __import__('duration').parse_duration({text!r}))()" for text in ["1x", "1m1h", "abc", "1.5h"]})
bad_type = {"int": "90", "none": "None", "bytes": "b'1h'", "float": "1.5", "list": "['1h']"}
cases.update({f"bt:{name}": f"parse_duration({expr})" for name, expr in bad_type.items()})
format_ok = {0: "0s", 59: "59s", 60: "1m", 3600: "1h", 86400: "1d", 604800: "1w", 5400: "1h30m", 3601: "1h1s",
             90061: "1d1h1m1s", 694861: "1w1d1h1m1s", 1209600: "2w", 61: "1m1s"}
cases.update({f"f:{seconds}": f"format_duration({seconds})" for seconds in format_ok})
cases.update({"fneg:-1": "format_duration(-1)", "fneg:-3600": "format_duration(-3600)"})
format_bad_type = {"float": "1.0", "bool": "True", "str": "'60'", "none": "None", "false": "False"}
cases.update({f"ft:{name}": f"format_duration({expr})" for name, expr in format_bad_type.items()})
round_trip = ["1h30m", "90", "2d 4h", "0s", "100000h", "59s", "1W", "01h05m", "1w2d3h4m5s", "3600"]
cases.update({f"rt:{text}": f"parse_duration(format_duration(parse_duration({text!r}))) == parse_duration({text!r})" for text in round_trip})

exists = (WORK / "duration.py").is_file()
results = run_cases(WORK, SETUP, cases) if exists else {name: {"ok": False, "error": "duration.py missing"} for name in cases}


def group(prefix, names):
    return {f"{prefix}:{name}": results[f"{prefix}:{name}"] for name in names}


def expect_values(check_id, requirement, texts):
    subset = {f"p:{t}": results[f"p:{t}"] for t in texts}
    ok, detail = all_equal(subset, {f"p:{t}": parse_ok[t] for t in texts})
    checks.add(check_id, requirement, ok, detail)


expect_values("parse-units", "R1", ["45s", "2m", "1h", "1d", "1w", "1h30m", "1w2d3h4m5s", "0s", "100000h"])
expect_values("whitespace-allowed", "R2", ["2d 4h", "  1h30m  ", "1h  30m"])
ok, detail = all_raise(results, ["bv:1 h"], "ValueError")
checks.add("whitespace-inside-component", "R2", ok, detail)
expect_values("case-insensitive", "R3", ["1H30M", "1W", "2D4h"])
expect_values("bare-integer", "R4", ["90", " 90 ", "0"])
ok, detail = all_raise(results, ["bv:1h30", "bv:h1"], "ValueError")
checks.add("component-needs-unit", "R4", ok, detail)
expect_values("leading-zeros", "R5", ["01h05m", "090", "007s"])
ok, detail = all_raise(results, ["bv:1m1h", "bv:1d1d", "bv:1s1w", "bv:1h1h30m"], "ValueError")
checks.add("order-and-repeats", "R6", ok, detail)
ok, detail = all_raise(results, [f"bv:{t}" for t in ["", "   ", "1x", "h", "-1h", "+1h", "1.5h", "abc", "1h-30m"]], "ValueError")
checks.add("invalid-raises-valueerror", "R7", ok, detail)
missing = [name[4:] for name in ("msg:1x", "msg:1m1h", "msg:abc", "msg:1.5h")
           if not (raised(results[name], "ValueError") and name[4:] in results[name].get("error", ""))]
checks.add("message-names-input", "R7", not missing, "message lacks the input for: " + ", ".join(missing) if missing else "")
ok, detail = all_raise(results, [f"bt:{name}" for name in bad_type], "TypeError")
checks.add("non-str-typeerror", "R8", ok, detail)
ok, detail = all_equal({f"f:{s}": results[f"f:{s}"] for s in format_ok}, {f"f:{s}": want for s, want in format_ok.items()})
checks.add("format-canonical", "R9", ok, detail)
ok, detail = all_raise(results, ["fneg:-1", "fneg:-3600"], "ValueError")
checks.add("format-negative", "R10", ok, detail)
ok, detail = all_raise(results, [f"ft:{name}" for name in format_bad_type], "TypeError")
checks.add("format-non-int", "R10", ok, detail)
ok, detail = all_equal({f"rt:{t}": results[f"rt:{t}"] for t in round_trip}, {f"rt:{t}": True for t in round_trip})
checks.add("round-trip", "R11", ok, detail)

# R12: the candidate's own tests
test_file = WORK / "test_duration.py"
methods = 0
if test_file.is_file():
    try:
        tree = ast.parse(test_file.read_text(encoding="utf-8"))
        methods = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
                      for item in node.body if isinstance(item, ast.FunctionDef) and item.name.startswith("test"))
    except (SyntaxError, UnicodeDecodeError):
        methods = 0
checks.add("tests-count", "R12", methods >= 12, f"{methods} test methods found", kind="requirement")
ran = run([sys.executable, "-m", "unittest", "test_duration"], WORK, timeout=120) if test_file.is_file() else {"code": 1, "err": "missing"}
checks.add("tests-pass", "R12", ran["code"] == 0, (ran.get("err") or "").strip().splitlines()[-1:][0][:200] if ran.get("err") else "", kind="requirement")

# R13: scope
files = visible_files(WORK)
extra = [name for name in files if name not in ("duration.py", "test_duration.py")]
checks.add("no-extra-files", "R13", exists and not extra, "extra files: " + ", ".join(extra[:5]) if extra else "", kind="scope")
stdlib = getattr(sys, "stdlib_module_names", None)
foreign = []
if stdlib:
    for name in ("duration.py", "test_duration.py"):
        path = WORK / name
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            foreign.append(f"{name} does not parse")
            continue
        for node in ast.walk(tree):
            modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else \
                      [node.module or ""] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
            foreign += [m for m in modules if m.split(".")[0] not in stdlib and m.split(".")[0] != "duration"]
checks.add("stdlib-only", "R13", exists and not foreign, "non-stdlib imports: " + ", ".join(foreign[:5]) if foreign else "", kind="scope")

checks.emit()
