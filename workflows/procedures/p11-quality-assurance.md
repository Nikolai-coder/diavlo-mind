# P11 — Quality assurance

## Trigger
- You are deciding what to test and how, or
- an artifact is about to be handed to someone who will rely on it, or
- the task's cost of failure is higher than its size suggests.

## Inputs
- Requirement list with acceptance criteria.
- The artifact: code, document, data, design, media.
- What can be executed or inspected in this environment.

## Protocol
1. **Rank by risk.** List what would hurt most if wrong: data loss, wrong numbers, security holes, broken public interfaces, the main user flow. Spend checks there first.
2. **Cover five kinds of case** for each important behaviour:
   - the normal case,
   - each boundary named in the requirements (empty, zero, one, maximum, exactly at the limit),
   - invalid input and the error it should produce,
   - the failure of something it depends on,
   - a regression check for every defect already found.
3. **Choose the cheapest check that could fail.** A unit test for logic, a command run for a CLI, a rendered page for a layout, a recomputed total for a spreadsheet, a second reading for a document. A check that cannot fail is not a check.
4. **Use the static checks the project already has:** compile, lint, type-check, link check, schema validation, spell check.
5. **Test the artifact as it will be used.** Open the file, run the documented command from a clean directory, follow your own instructions step by step.
6. **Review from three chairs:** the user (does it do what I asked?), the maintainer (can I understand and change it?), the adversary (how do I break or misuse it?).
7. **For non-code work, check against the format's rules:** length limits, required sections, naming, numbers that must add up, links that must resolve, claims that need sources.
8. **Record results as evidence:** the command or inspection, and what it showed.

## Tools
- The project's test runner, linter and type checker.
- Scratch scripts for recomputing numbers or validating structure.
- A browser or renderer for anything visual.
- A reviewer agent (`agents/dm-reviewer.md`) for a fresh reading.

## Outputs
- A short test plan: behaviour, cases, check.
- Executed results with pass or fail for each.
- A list of defects found, each with location and severity.
- A statement of what was not tested and why.

## Verification
- Every requirement has at least one executed check, or is listed as not verified.
- Each high-risk item has more than the normal case.
- Checks were run after the last change, not before it.
- The untested list is explicit, not implied.

## Recovery
- **Cannot execute tests here:** say NOT RUN, perform the static checks and a careful read-through, and give the exact commands for the user.
- **A check is flaky:** it is a defect in the check or the code. Find which; do not rerun until it passes and call that success.
- **Too many failures to fix in scope:** stop, group them by cause, fix the cause with the widest effect, and report the rest.
- **Tests pass but the result still looks wrong:** trust the observation. The tests are missing a case — add it.
