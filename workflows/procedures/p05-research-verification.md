# P05 — Efficient research and information verification

## Trigger
- An answer depends on facts you are not certain of, or that may have changed (versions, prices, APIs, laws, who holds a role), or
- you are about to rely on a library, service or format you have not used in this session, or
- sources disagree.

## Inputs
- The question, and the decision it feeds.
- Available sources: the codebase, local documents, the web, people.

## Protocol
1. **State the question and the decision.** Write what would change depending on the answer. If nothing changes, do not research.
2. **Split it** into the few sub-questions that must be true for the answer to hold.
3. **Go to primary sources first:** official documentation, specifications, source code, changelogs, release notes, the data itself. Use secondary sources to find primary ones, not to replace them.
4. **Check freshness.** Note each source's date and version. Prefer the source that matches the version actually in use.
5. **Triangulate what matters.** A claim that decides the outcome needs two independent sources, or one primary source plus a direct test.
6. **Test instead of reading when a test is cheap.** A five-line script settles more than five articles.
7. **Record as you go:** `claim · source · date or version · level`. Levels are VERIFIED (you ran it), SOURCED (primary source read), ASSUMED, UNKNOWN.
8. **Resolve conflicts explicitly.** Say which source wins and why (newer, more authoritative, matches the tested behaviour). An unresolved conflict is reported as unresolved.
9. **Stop** when the sub-questions are answered at the needed level, or new sources stop changing the answer, or the budget is spent. Report what remains UNKNOWN.
10. **Answer first, then the evidence.** Lead with the conclusion, follow with the table and the open points.

## Tools
- Code and document search for local truth.
- Web search with specific queries; fetch the primary page rather than trusting the snippet.
- A scratch script or REPL for direct tests.
- A researcher subagent (`agents/dm-researcher.md`) when digging would flood your context; ask it for conclusions with sources.

## Outputs
```
Answer: <one or two sentences>
| Claim | Source | Date/version | Level |
| Default port is 7411 | official docs, "Configuration" | v3.2 | SOURCED |
| Port 7400 still accepted | started server with --port 7400 | v3.2.1 | VERIFIED |
Conflicts: blog post (2023) says 7400 is the default — outdated, describes v2.
Unknown: licence of the enterprise plugin — not stated in any source found.
```

## Verification
- Every claim in the answer appears in the table with a source.
- Nothing labelled SOURCED relies only on a blog, forum or summary.
- Dates and versions are present for anything time-sensitive.
- Unknowns are listed rather than filled with plausible guesses.

## Recovery
- **No primary source exists:** say so, give the best secondary evidence labelled ASSUMED, and propose the test or contact that would settle it.
- **Sources contradict and cannot be ranked:** present both, state the practical consequence of each, recommend the safer assumption.
- **Search returns nothing useful:** change the query shape (exact error text, function name, version number) once or twice, then stop and report the gap.
- **You cannot access the source** (paywall, blocked site, no network): do not reconstruct it from memory; report it as unreachable.
