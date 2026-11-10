#!/usr/bin/env python3
"""Hidden checks for debugging-inventory. Usage: check.py <workspace>"""
import ast
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "lib"))
from checklib import Checks, read_text, run, run_cases, workspace_arg  # noqa: E402

WORK = workspace_arg()
checks = Checks()
ORIGINAL_TESTS = ["test_add_and_total_value", "test_add_rejects_duplicate_sku", "test_restock_adds_to_existing_quantity",
                  "test_restock_rejects_non_positive", "test_remove", "test_unknown_sku", "test_low_stock_below_threshold",
                  "test_discount_whole_cents", "test_discount_rejects_bad_percent", "test_line_total", "test_export_simple"]

SETUP = """
import csv, inspect, io
from inventory import Inventory, Item, apply_discount, export_csv
from inventory.pricing import line_total

def restocked():
    inv = Inventory({})
    inv.add(Item("A-100", "Washer", 5, 25))
    first = inv.restock("A-100", 3)
    second = inv.restock("A-100", 2)
    return [first, second, inv.items["A-100"].quantity]

def isolation():
    first = Inventory()
    first.add(Item("X-1", "x", 1, 1))
    second = Inventory()
    return [len(second.items), first.items is second.items, len(Inventory().items)]

def explicit_dict_still_used():
    inv = Inventory({})
    inv.add(Item("K-1", "k", 2, 3))
    return inv.total_value()

def exported(names):
    inv = Inventory({})
    for index, name in enumerate(names):
        inv.add(Item("S-%d" % index, name, index + 1, 100 + index))
    return list(csv.reader(io.StringIO(export_csv(inv))))

def simple_export():
    inv = Inventory({})
    inv.add(Item("A-100", "Washer", 5, 25))
    inv.add(Item("B-200", "Bolt", 40, 110))
    return export_csv(inv)

def low(threshold):
    inv = Inventory({})
    for sku, quantity in (("L-3", 11), ("L-2", 10), ("L-1", 9), ("L-0", 0)):
        inv.add(Item(sku, sku, quantity, 1))
    return [item.sku for item in inv.low_stock(threshold)]

def parameters(function):
    return list(inspect.signature(function).parameters)
"""

NAMES = ["Bolt, hex (M8)", 'Nut "locking"', "Plain", "Semi; colon", "Trailing comma,"]
cases = {
    "restock": "restocked()",
    "isolation": "isolation()",
    "explicit": "explicit_dict_still_used()",
    "csv": f"exported({NAMES!r})",
    "csv_simple": "simple_export()",
    "low10": "low(10)",
    "low0": "low(0)",
    "d1": "apply_discount(995, 15)", "d2": "apply_discount(105, 50)", "d3": "apply_discount(1, 50)",
    "d4": "apply_discount(999, 50)", "d5": "apply_discount(333, 10)", "d6": "apply_discount(1000, 25)",
    "d7": "apply_discount(1000, 0)", "d8": "apply_discount(1000, 100)", "d9": "line_total(995, 2, 15)",
    "api": "[parameters(Inventory.__init__), parameters(Inventory.add), parameters(Inventory.restock), "
           "parameters(Inventory.remove), parameters(Inventory.low_stock), parameters(Inventory.total_value), "
           "parameters(apply_discount), parameters(line_total), parameters(export_csv), "
           "[f for f in Item.__dataclass_fields__]]",
    "api_default": "[inspect.signature(line_total).parameters['percent'].default, type(apply_discount(1000, 25)).__name__, "
                   "type(export_csv(Inventory({}))).__name__, type(Inventory({}).low_stock(1)).__name__]",
}
results = run_cases(WORK, SETUP, cases)


def got(name):
    return results[name].get("value") if results[name].get("ok") else None


def detail(name):
    return "" if results[name].get("ok") else results[name].get("error", "")


checks.add("restock-accumulates", "R1", got("restock") == [8, 10, 10], detail("restock") or str(got("restock")))
checks.add("no-shared-items", "R2", got("isolation") == [0, False, 0] and got("explicit") == 6,
           detail("isolation") or str(got("isolation")))
expected_rows = [["sku", "name", "quantity", "price_cents"]] + [[f"S-{i}", name, str(i + 1), str(100 + i)] for i, name in enumerate(NAMES)]
checks.add("csv-round-trips", "R3", got("csv") == expected_rows, detail("csv") or str(got("csv"))[:200])
checks.add("csv-simple-unchanged", "R3", got("csv_simple") == "sku,name,quantity,price_cents\nA-100,Washer,5,25\nB-200,Bolt,40,110\n",
           detail("csv_simple") or repr(got("csv_simple"))[:200])
checks.add("low-stock-at-threshold", "R4", got("low10") == ["L-0", "L-1", "L-2"] and got("low0") == ["L-0"],
           detail("low10") or f"{got('low10')} / {got('low0')}")
discounts = {"d1": 846, "d2": 53, "d3": 1, "d4": 500, "d5": 300, "d6": 750, "d7": 1000, "d8": 0, "d9": 1692}
wrong = [f"{name}={got(name)!r} (want {want})" for name, want in discounts.items() if got(name) != want]
checks.add("discount-half-up", "R5", not wrong, "; ".join(wrong[:4]))

# R6: the candidate's whole suite
suite = run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], WORK, timeout=180)
tail = (suite["err"] or suite["out"]).strip().splitlines()[-1:] or [""]
checks.add("suite-passes", "R6", suite["code"] == 0, tail[0][:200], kind="requirement")

# R8: public API
expected_api = [["self", "items"], ["self", "item"], ["self", "sku", "quantity"], ["self", "sku", "quantity"],
                ["self", "threshold"], ["self"], ["price_cents", "percent"], ["price_cents", "quantity", "percent"],
                ["inventory"], ["sku", "name", "quantity", "price_cents"]]
checks.add("public-api-unchanged", "R8", got("api") == expected_api and got("api_default") == [0, "int", "str", "list"],
           detail("api") or f"{got('api')} {got('api_default')}", kind="scope")

# R9: minimal change. A module counts as rewritten when fewer than half of its original
# non-blank lines survive. (Until benchmark revision 2 this was a similarity ratio with a 0.60
# threshold, which the reference fix itself passed by only 0.04 on the 12-line report.py.)
kept = {}
for name in ("models.py", "pricing.py", "report.py"):
    new = read_text(WORK / "inventory" / name)
    original = [line for line in read_text(HERE / f"original_{name}").splitlines() if line.strip()]
    surviving = set((new or "").splitlines())
    kept[name] = sum(1 for line in original if line in surviving) / len(original) if new is not None else 0.0
checks.add("modules-not-rewritten", "R9", all(share >= 0.5 for share in kept.values()),
           "original lines kept: " + ", ".join(f"{n} {share:.2f}" for n, share in kept.items()), kind="scope")
found = set()
for path in (WORK / "tests").rglob("*.py") if (WORK / "tests").is_dir() else []:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        continue
    found |= {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
missing = [name for name in ORIGINAL_TESTS if name not in found]
checks.add("existing-tests-kept", "R9", not missing, "removed: " + ", ".join(missing) if missing else "", kind="scope")

# R7: does the candidate's suite catch each defect when it is put back?
MUTANTS = [("bug1", "models.py"), ("bug2", "models.py"), ("bug3", "report.py"), ("bug4", "models.py"), ("bug5", "pricing.py")]
with tempfile.TemporaryDirectory() as scratch:
    copy = Path(scratch) / "work"
    if (WORK / "inventory").is_dir() and (WORK / "tests").is_dir():
        shutil.copytree(WORK, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
        for name in ("models.py", "pricing.py", "report.py"):
            shutil.copyfile(HERE / f"fixed_{name}", copy / "inventory" / name)
        compatible = run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], copy, timeout=180)["code"] == 0
    else:
        compatible = False
    for bug, module in MUTANTS:
        if not compatible:
            checks.add(f"regression-test-{bug}", "R7", False,
                       "the test suite does not pass against a correct implementation with the same public API", kind="requirement")
            continue
        for name in ("models.py", "pricing.py", "report.py"):
            shutil.copyfile(HERE / f"fixed_{name}", copy / "inventory" / name)
        shutil.copyfile(HERE / "mutants" / f"{bug}_{module}", copy / "inventory" / module)
        outcome = run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], copy, timeout=180)
        checks.add(f"regression-test-{bug}", "R7", outcome["code"] != 0,
                   "" if outcome["code"] != 0 else "the suite still passes when this defect is reintroduced", kind="requirement")

checks.emit()
