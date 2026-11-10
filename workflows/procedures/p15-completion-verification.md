# P15 — Task completion verification

## Trigger
You are about to tell the user the task is done, or to mark a task `done` in project state.

## Inputs
- The requirement list with its checks.
- The artifact as it currently exists on disk or in the reply.
- The definition of done, if the project has one.

## Protocol
1. **Re-read the original request** — the actual words, not your summary of them. Requirements drift during work.
2. **Run the acceptance checks now,** after the last change, from as clean a state as you can get: fresh shell, clean directory, re-opened file.
3. **Walk the requirement list** one row at a time against the artifact itself. For each row record *met* with evidence, *unmet* with reason, or *not verified* with what is missing.
4. **Use the artifact the way the user will.** Open the document, run the documented command, follow your own instructions, click the link. Check that the file is where you say it is.
5. **Check for debris:** debug output, temporary files, commented-out code, TODOs you added, credentials, absolute paths from your environment.
6. **Check the scope:** list the files changed and confirm each change belongs to the task.
7. **Check your claims.** Every statement in the report that says something works must correspond to something you executed or inspected in this session. Replace the rest with NOT RUN, ASSUMED or UNKNOWN.
8. **Choose the status honestly:**
   - **DONE** — every acceptance check is VERIFIED.
   - **PARTIAL** — some requirements are unmet or unverified; list them.
   - **BLOCKED** — you cannot proceed without something; name it.
   - **FAILED** — the approach did not work; give evidence and the next experiment.
9. **Write the delivery block** from `SKILL.md`: result, status, evidence table, gaps, assumptions, next step.

## Tools
- The project's test and build commands; a fresh shell.
- `git status` and `git diff --stat` or a file listing.
- `scripts/dm_state.py done-check` in long projects.
- A validator agent (`agents/dm-validator.md`) when independence matters.

## Outputs
The delivery block, with one evidence row per requirement.

## Verification
- The number of rows in the evidence table equals the number of requirements.
- Each "met" row cites an execution or inspection performed after the final change.
- The status matches the table: DONE is impossible with any unmet or unverified *must* requirement.
- A reader could repeat every check from the report alone.

## Recovery
- **A check fails at this stage:** you are not done. Fix it and restart this procedure from step 2, or deliver as PARTIAL with the failure shown.
- **You cannot run a check:** the row says NOT RUN and gives the exact command. The status is at most PARTIAL for anything that matters.
- **You find a missed requirement:** add it to the list, do it or report it unmet. Never drop it to keep the status DONE.
- **Time or budget ran out:** deliver what is verified, labelled PARTIAL, with the remaining work ordered by importance.
