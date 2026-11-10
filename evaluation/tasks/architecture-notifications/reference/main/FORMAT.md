# Deliverable format

## DESIGN.md

Use exactly these second-level headings, in this order:

```
## Context
## Components
## Data flow
## Interfaces
## Decisions
## Risks
## Test strategy
```

Refer to every requirement (R1–R8) and every constraint (C1–C3) by its id at least once. Length: between 2,500 and 20,000 characters.

## architecture.json

One JSON object with these keys:

```json
{
  "components": [
    {"id": "kebab-case-id", "responsibility": "one sentence, at least 20 characters",
     "depends_on": ["other-component-id"], "satisfies": ["R1"]}
  ],
  "interfaces": [
    {"name": "…", "provider": "component-id", "consumers": ["component-id"],
     "input": "…", "output": "…", "errors": ["at least one error case"]}
  ],
  "decisions": [
    {"id": "D1", "question": "…", "options": ["at least two", "real options"], "chosen": "exactly one of the options",
     "rationale": "…", "tradeoffs": "what the choice costs", "revisit_if": "what would reopen it"}
  ],
  "requirement_map": {"R1": ["component-id"], "R2": ["component-id"]},
  "constraints": {"C1": "how the design satisfies it, at least 30 characters", "C2": "…", "C3": "…"},
  "risks": [
    {"risk": "…", "mitigation": "…", "validation": "the experiment or test that would show the risk is real"}
  ]
}
```

Rules:

- At least 3 components, 3 interfaces, 3 decisions and 3 risks.
- Component ids are unique. `depends_on` lists only existing component ids, and the dependency graph has no cycles.
- `requirement_map` has an entry for each of R1–R8, each listing at least one existing component id.
- `requirement_map` and `components[].satisfies` must agree: a component appears under a requirement exactly when that requirement appears in its `satisfies` list.
- `consumers` may also contain the word `external` for callers outside the service.
- `constraints` explains each of C1, C2 and C3.
