# P20 — Maintaining consistency across large projects

## Trigger
- The project has many files, several contributors or agents, or lasts many sessions, or
- the same name, value, format or rule appears in more than one place, or
- you are about to rename, restructure or change a shared interface.

## Inputs
- The existing conventions, written or implied by the code and documents.
- The interfaces and shared constants.
- The list of places that depend on what you are changing.

## Protocol
1. **Find the existing convention before inventing one.** Look at three or four neighbouring files: naming, layout, error handling, tests, wording. Follow what is there.
2. **Write the conventions down once,** in a single file (`CONVENTIONS.md`): names, folder structure, code style, interface rules, terminology, versioning. Agents and people read it before contributing.
3. **Keep one source of truth** for each shared thing — a constant, a schema, a version number, a list of supported options. Everything else refers to it or is generated from it. Where duplication is unavoidable, add a check that fails when the copies differ.
4. **Define interfaces as contracts** and change them deliberately: announce the change, update every caller in the same change, keep a compatibility path or state that there is none.
5. **Maintain a glossary** for the project's own terms. One concept, one word.
6. **Sweep after every rename or format change.** Search the whole project — code, tests, documentation, configuration, examples — for the old name or pattern. A rename is finished when the search returns nothing unintended.
7. **Log decisions with reasons** so a later contributor does not undo them unknowingly.
8. **Run consistency checks regularly:** links resolve, versions match across files, examples run, schemas validate, generated files are up to date. Automate the ones that can be automated.
9. **Integrate often.** Small merges checked against the whole beat a large merge at the end.
10. **Give every delegated task the conventions** by reference in its task packet, and reject returned work that ignores them.

## Tools
- Project-wide search for names, values and patterns.
- Linters, formatters, schema validators and link checkers.
- A validation script run locally and in CI (this repository uses `scripts/validate.py` for that purpose).
- Version control history to see why something is the way it is.

## Outputs
- `CONVENTIONS.md` and a glossary.
- A decision log.
- A consistency check that can be run on demand.
- After a rename or interface change: the list of places updated and the search that shows none remain.

## Verification
- A search for the old name or pattern returns only intended matches.
- Shared values agree everywhere they appear (the automated check passes).
- New files follow the conventions file; deviations are deliberate and recorded.
- Examples and documented commands still run.

## Recovery
- **Two conventions coexist:** pick one, record the decision, and convert the other in a separate, purely mechanical change.
- **Copies have drifted:** find the authoritative one, regenerate or correct the others, then add the check that would have caught it.
- **A rename was only partly applied:** finish it or revert it entirely; half-renamed is the worst state.
- **An agent returned inconsistent work:** send it back with the conventions file and the specific violations; do not hand-patch it into shape unrecorded.
