# P03 — Autonomous software engineering

## Trigger
You will create or change code in a repository or project folder.

## Inputs
- The requirement list and acceptance criteria.
- The repository: source, tests, build and run instructions, conventions.
- Permission boundaries: what you may run, install, commit or push.

## Protocol
1. **Learn the project's rules.** Read the README, contribution notes, agent instruction files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) and the build or test configuration. Find the exact commands to build, test and lint.
2. **Establish a baseline.** Run the existing tests before changing anything and record the result. Failures that already exist are noted and left alone unless they are the task.
3. **Locate before editing.** Search for the symbols, strings and call sites involved. Read every file you will change in full, and at least the signatures of what calls it.
4. **Reproduce first** when fixing a bug: a failing test or command that shows the bug. No reproduction, no fix.
5. **Change the minimum.** Follow the surrounding style, naming and error handling. Prefer editing existing code to adding parallel code. Add no dependency unless the task needs it, and say so when you do.
6. **Check after each change.** Run the narrowest test that covers it. Then run the wider suite before declaring the step done.
7. **Write the tests the change deserves:** the happy path, each boundary named in the requirements, and each failure mode you handled. A bug fix always gets a regression test.
8. **Review your own diff** as a stranger would: unrelated edits, leftover debug output, secrets, commented-out code, missing error handling at inputs and I/O boundaries.
9. **Leave the workspace clean.** Remove temporary files. Do not commit, push, publish or deploy unless asked.

## Tools
- Search (grep, ripgrep, IDE search) before reading; targeted file reads over whole-tree dumps.
- The project's own test, lint and type-check commands.
- Version control: `git status` and `git diff` to confirm the scope of the change.
- A sandbox or scratch directory for experiments, never the user's data.

## Outputs
- The code change, limited to what the requirements need.
- Tests that fail without the change and pass with it.
- A report: files changed, commands run with results, anything not verified.

## Verification
- Baseline result versus final result is stated (for example "12 passed → 15 passed, 0 failed").
- Each requirement maps to a test or an observed behaviour.
- `git diff --stat` (or the file list) shows only intended files.
- Build, lint and type checks that exist in the project pass, or their failures are reported as pre-existing with evidence.

## Recovery
- **Tests cannot run** (missing dependency, no network): say NOT RUN, give the exact command, and verify what you can statically (syntax check, reading the code path).
- **A test fails after your change:** read the full error, do not guess. Fix the cause. Never edit or delete a test to make it pass unless the test itself is wrong, and then say why.
- **The change keeps growing:** stop and return to P01; you are solving a larger problem than you framed.
- **You broke something unrelated:** revert that part, confirm the baseline, and re-apply the change more narrowly.
