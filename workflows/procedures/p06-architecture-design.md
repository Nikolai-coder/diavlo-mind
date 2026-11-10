# P06 — Architecture design

## Trigger
- A new system, a new major component, or a restructuring of an existing one, or
- a change to how components communicate, store data or are deployed.

## Inputs
- Requirements, with quality attributes made explicit (performance, reliability, security, cost, operability).
- Constraints: platform, team skills, existing systems, budget, deadline.
- The current structure, if one exists.

## Protocol
1. **List the drivers.** Pick the three to five requirements and constraints that actually shape the design. Give each a measurable form where possible ("p95 under 200 ms", "runs on one VM").
2. **Read the current structure** before proposing a new one: entry points, data stores, boundaries, what is painful and what works.
3. **Name the components.** One responsibility each, described in a sentence without "and". For each: what it owns, what it must never do.
4. **Trace the main flows** end to end: the common request, the largest input, and the failure of each external dependency.
5. **Define the contracts** between components before any implementation: inputs, outputs, errors, invariants, ownership of data, versioning. A contract is concrete enough that two people could implement each side separately.
6. **Generate at least two real options** for each key decision, including the simplest thing that could work. Compare them against the drivers in a table (`p14-tradeoff-analysis`).
7. **Decide and record.** One decision record per key choice: context, options, decision, consequences, what would make you revisit it.
8. **Check for structural faults:** dependency cycles, shared mutable state, a component that knows too much, a single point of failure that the drivers forbid.
9. **Plan the proof.** Name the experiment or thin slice that would show the design is wrong, and schedule it first.
10. **Set the standards** the implementation must follow — naming, layout, error handling, logging, testing — in a conventions file.

## Tools
- Code search and dependency listing to see the real structure.
- A text diagram (lists or Mermaid) kept next to the code.
- `prompts/templates/decision-record.md` for decisions; `memory/templates/CONVENTIONS.md` for standards.

## Outputs
- Driver list.
- Component table: name, responsibility, owns, depends on.
- Interface contracts.
- Decision records with rejected alternatives.
- Risks and the experiment that addresses each.
- Conventions.

## Verification
- Every requirement maps to at least one component; every component serves at least one requirement.
- The dependency graph has no cycles.
- Every contract states its error cases.
- Each key decision lists at least two options and the reason for the choice.
- The design satisfies every stated constraint, one by one, in writing.

## Recovery
- **An experiment disproves the design:** update the decision record with the new evidence and choose again. Do not patch around a wrong foundation.
- **Requirements conflict** (for example, strongest consistency and lowest latency): surface the conflict to the user with the options and their costs; do not pick silently.
- **The design is getting complicated:** remove a component and see which driver breaks. If none does, it was not needed.
- **Implementation drifts from the design:** either fix the code or change the record. A design document that no longer matches the system is worse than none.
