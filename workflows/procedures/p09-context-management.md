# P09 — Context management

## Trigger
- The conversation or working set is large or long-running, or
- context was compacted, summarized or restarted, or
- you notice you are relying on your memory of a file rather than the file.

## Inputs
- The requirement list and the current plan.
- The notes or state files, if any exist.
- A rough sense of how much context remains.

## Protocol
1. **Keep the anchor small and fixed.** The objective, requirement list and current step should fit in a few lines and be easy to re-read. In long work they live in a file.
2. **Externalize facts as you learn them.** One line each: the fact, where it came from. Notes go to a file (`NOTES.md`, or `.diavlo-mind/` in AUTONOMOUS mode), not only into the conversation.
3. **Pull in only what the current step needs.** Search first, then read the relevant range. Do not paste whole files, logs or pages when twenty lines answer the question.
4. **Summarize large results at once.** After a long tool output, write the two or three facts you took from it; rely on those and the source, not on scrolling back.
5. **Re-read instead of remembering.** Before editing a file, read its current content. Before citing a requirement, look at the list. Files change; memory drifts.
6. **Delegate the bulky digging.** Exploration that produces a lot of text and a short answer belongs in a subagent that returns the answer.
7. **Checkpoint before the limit.** When context is getting full, write a checkpoint: what is done, what is in progress, the next action, open questions, and the exact files involved.
8. **After compaction or restart, reload on purpose:** the requirement list, the plan, the last checkpoint, then the files for the current step. Verify the checkpoint against the real files before trusting it.
9. **Drop what is finished.** Once a step is verified and recorded, stop carrying its details.

## Tools
- Search and ranged reads.
- A notes or state file; `scripts/dm_state.py checkpoint` and `resume`.
- Subagents for high-volume exploration.
- The host's own compaction or memory features, where they exist.

## Outputs
- A current notes file with facts and sources.
- A checkpoint whenever work pauses or context is about to roll over.

## Verification
- A fresh session could continue from the files alone: test this by reading only the checkpoint and asking whether the next action is unambiguous.
- Every fact you act on is in the notes with a source, or freshly read.
- The requirement list in use is the written one, not a remembered paraphrase.

## Recovery
- **You lost track of the task:** stop acting. Re-read the requirement list and the last checkpoint, then list what the files actually show.
- **Notes and files disagree:** the files win. Correct the notes and record the discrepancy.
- **A requirement was dropped after compaction:** restore it from the written list and re-check the work done since.
- **No notes exist and context is already gone:** rebuild from the artifacts — diff, file dates, test results — and tell the user what could not be recovered.
