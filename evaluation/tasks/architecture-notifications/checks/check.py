#!/usr/bin/env python3
"""Hidden checks for architecture-notifications. Usage: check.py <workspace>

These checks measure structure and discipline: completeness, internal
consistency and respect for the stated constraints. They do not judge whether
the design is a good one; evaluation/rubrics/architecture.md covers that.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from checklib import Checks, read_json, read_text, visible_files, workspace_arg  # noqa: E402

WORK = workspace_arg()
checks = Checks()
REQS = [f"R{i}" for i in range(1, 9)]
CONS = ["C1", "C2", "C3"]
KEYS = ["components", "interfaces", "decisions", "requirement_map", "constraints", "risks"]
SECTIONS = ["Context", "Components", "Data flow", "Interfaces", "Decisions", "Risks", "Test strategy"]


def fold(heading):
    return re.sub(r"\s+", " ", heading).strip().lower()


def spelled(value):
    """Lower-case words separated by single spaces: 'rate-limiter' and 'Rate Limiter' both give 'rate limiter'."""
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def named_in(design_words, component_id):
    words = spelled(component_id)
    if not words:
        return False
    if f" {words} " in design_words:
        return True
    return " " in words and words.replace(" ", "") in design_words.replace(" ", "")
FORBIDDEN = ["redis", "kafka", "rabbitmq", "sqs", "sns", "mongodb", "dynamodb", "elasticsearch", "cassandra", "memcached",
             "kubernetes", "k8s", "nomad", "lambda", "celery", "nats", "pubsub", "mysql", "sqlite", "kinesis"]

data = read_json(WORK / "architecture.json")
valid = isinstance(data, dict) and all(key in data for key in KEYS)
missing = [key for key in KEYS if not (isinstance(data, dict) and key in data)]
checks.add("json-valid", "R1", valid, "missing keys: " + ", ".join(missing) if missing else "", kind="requirement")
data = data if isinstance(data, dict) else {}


def items(key, kind=list):
    value = data.get(key)
    return value if isinstance(value, kind) else kind()


def text(value, minimum=1):
    return isinstance(value, str) and len(value.strip()) >= minimum


components = [c for c in items("components") if isinstance(c, dict)]
ids = [c.get("id") for c in components]
id_set = {i for i in ids if isinstance(i, str)}
problems = []
if len(components) < 3:
    problems.append(f"only {len(components)} components")
if len(ids) != len(id_set):
    problems.append("ids are missing or not unique")
for component in components:
    if not text(component.get("responsibility"), 20):
        problems.append(f"{component.get('id')}: responsibility shorter than 20 characters")
    for dep in component.get("depends_on") or []:
        if dep not in id_set:
            problems.append(f"{component.get('id')} depends on unknown component {dep}")
checks.add("components-well-formed", "R2", not problems, "; ".join(problems[:4]), kind="requirement")

graph = {c.get("id"): [d for d in (c.get("depends_on") or []) if d in id_set] for c in components if isinstance(c.get("id"), str)}
state, cycle = {}, []


def visit(node, trail):
    state[node] = 1
    for dep in graph.get(node, []):
        if state.get(dep) == 1:
            cycle.extend(trail + [node, dep])
            return True
        if dep not in state and visit(dep, trail + [node]):
            return True
    state[node] = 2
    return False


has_cycle = any(visit(node, []) for node in list(graph) if node not in state)
checks.add("dependencies-acyclic", "R2", bool(graph) and not has_cycle, " -> ".join(map(str, cycle[:6])), kind="requirement")

mapping = items("requirement_map", dict)
problems = []
for requirement in REQS:
    targets = mapping.get(requirement)
    if not isinstance(targets, list) or not targets:
        problems.append(f"{requirement} is not mapped")
    elif any(target not in id_set for target in targets):
        problems.append(f"{requirement} maps to an unknown component")
checks.add("requirements-mapped", "R3", not problems, "; ".join(problems[:4]), kind="requirement")

from_map = {(req, comp) for req, comps in mapping.items() if isinstance(comps, list) for comp in comps if req in REQS}
from_components = {(req, c.get("id")) for c in components for req in (c.get("satisfies") or []) if req in REQS}
difference = sorted(from_map ^ from_components)
checks.add("map-and-satisfies-agree", "R3", bool(from_map) and not difference,
           "disagree on: " + ", ".join(f"{r}/{c}" for r, c in difference[:5]) if difference else "", kind="requirement")

constraints = items("constraints", dict)
weak = [name for name in CONS if not text(constraints.get(name), 30)]
checks.add("constraints-explained", "R4", not weak, "missing or too short: " + ", ".join(weak) if weak else "", kind="requirement")

interfaces = [i for i in items("interfaces") if isinstance(i, dict)]
problems = [] if len(interfaces) >= 3 else [f"only {len(interfaces)} interfaces"]
for interface in interfaces:
    name = interface.get("name")
    if interface.get("provider") not in id_set:
        problems.append(f"{name}: unknown provider")
    consumers = interface.get("consumers")
    if not isinstance(consumers, list) or not consumers or any(c not in id_set and c != "external" for c in consumers):
        problems.append(f"{name}: consumers missing or unknown")
    if not (text(interface.get("input")) and text(interface.get("output"))):
        problems.append(f"{name}: input or output missing")
    errors = interface.get("errors")
    if not isinstance(errors, list) or not errors or not all(text(e) for e in errors):
        problems.append(f"{name}: no error case")
checks.add("interfaces-complete", "R5", not problems, "; ".join(problems[:4]), kind="requirement")

decisions = [d for d in items("decisions") if isinstance(d, dict)]
problems = [] if len(decisions) >= 3 else [f"only {len(decisions)} decisions"]
for decision in decisions:
    name = decision.get("id")
    options = decision.get("options")
    if not isinstance(options, list) or len(options) < 2:
        problems.append(f"{name}: fewer than two options")
    elif decision.get("chosen") not in options:
        problems.append(f"{name}: chosen is not one of the options")
    for field in ("question", "rationale", "tradeoffs", "revisit_if"):
        if not text(decision.get(field), 5):
            problems.append(f"{name}: {field} missing")
checks.add("decisions-complete", "R6", not problems, "; ".join(problems[:4]), kind="requirement")

risks = [r for r in items("risks") if isinstance(r, dict)]
problems = [] if len(risks) >= 3 else [f"only {len(risks)} risks"]
for index, risk in enumerate(risks):
    for field in ("risk", "mitigation", "validation"):
        if not text(risk.get(field), 5):
            problems.append(f"risk {index + 1}: {field} missing")
checks.add("risks-complete", "R7", not problems, "; ".join(problems[:4]), kind="requirement")

# Constraint C1/C2: look only at what was chosen and at component ids, so that
# a design may still mention rejected technologies in its options.
chosen_text = " ".join(str(d.get("chosen", "")) for d in decisions).lower() + " " + " ".join(i.lower() for i in id_set)
used = sorted({word for word in FORBIDDEN if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", chosen_text)})
checks.add("constraints-respected", "R8", bool(decisions) and not used,
           "chosen design uses: " + ", ".join(used) if used else "", kind="requirement")

design = read_text(WORK / "DESIGN.md") or ""
headings = [line[3:].strip() for line in design.splitlines() if line.startswith("## ")]
# FORMAT.md gives the headings; a difference in letter case only ("Data Flow") is not a missing section.
wanted = [fold(section) for section in SECTIONS]
order_ok = [fold(h) for h in headings if fold(h) in wanted] == wanted
checks.add("design-sections", "R9", order_ok, f"found: {headings}"[:300], kind="requirement")
unmentioned = [name for name in REQS + CONS if not re.search(rf"\b{name}\b", design)]
checks.add("design-refers-to-ids", "R9", bool(design) and not unmentioned,
           "not mentioned: " + ", ".join(unmentioned) if unmentioned else "", kind="requirement")
checks.add("design-length", "R9", 2500 <= len(design) <= 20000, f"{len(design)} characters", kind="requirement")
# The brief asks that the two files agree, not that the document spells ids in kebab case:
# "Rate Limiter", "rate limiter" and "RateLimiter" all name the component `rate-limiter`.
design_words = f" {spelled(design)} "
component_gaps = [name for name in id_set if not named_in(design_words, name)]
checks.add("design-names-components", "R9", bool(id_set) and not component_gaps,
           "components absent from DESIGN.md: " + ", ".join(sorted(component_gaps)[:5]) if component_gaps else "", kind="requirement")

extra = [name for name in visible_files(WORK) if name not in ("BRIEF.md", "FORMAT.md", "DESIGN.md", "architecture.json")]
checks.add("no-extra-files", "R9", not extra and bool(design), "extra files: " + ", ".join(extra[:5]) if extra else "", kind="scope")

checks.emit()
