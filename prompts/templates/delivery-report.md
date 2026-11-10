# Delivery report

End STANDARD, DEEP and AUTONOMOUS work with this block and nothing after it.

```
Result: <what was produced and where it is>
Status: DONE | PARTIAL | BLOCKED | FAILED
Evidence:
| Req | Status | Evidence |
|-----|--------|----------|
| R1 | met — VERIFIED | `<command>` → <result> |
| R2 | met — SOURCED | <doc, section> |
| R3 | unmet | <reason> |
| R4 | not verified | NOT RUN: `<exact command>` |
Not done / not verified: <list, or "nothing">
Assumptions: <list, or "none">
Next step: <one concrete action>
```

For DEEP and AUTONOMOUS add, above the block:

- **Decisions:** one line each — what was chosen, why, what was rejected.
- **Known limitations:** what the result does not handle.
- **How to run / roll back:** the commands.
- **Agents used:** role → model (when more than one was involved).

Keep it short. The table is the summary; do not restate it in prose.
