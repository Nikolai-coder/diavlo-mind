# P13 — Creative problem-solving

## Trigger
- You are stuck: the obvious approaches failed or do not exist, or
- the task is open-ended (naming, concept, script, design, strategy), or
- the first idea arrived instantly and you have not compared it with anything.

## Inputs
- The real goal behind the request, and who the result is for.
- Hard constraints (length, format, budget, platform, brand rules) and soft preferences.
- What has already been tried, and why it fell short.

## Protocol
1. **Restate the goal one level up.** Ask what the result is for. "A faster cache" may really be "the page loads in under a second", which admits other solutions.
2. **Separate hard constraints from habits.** List the constraints; mark each as stated by the user, imposed by reality, or merely assumed. Assumed ones are candidates to drop.
3. **Diverge before judging.** Produce at least three materially different candidates — different mechanism or angle, not three wordings. Useful prompts:
   - *simplest* — what is the least that would work?
   - *inversion* — what would guarantee failure? Avoid that.
   - *analogy* — where has a similar problem been solved?
   - *remove a constraint* — what if one limit did not exist? Can you get most of that benefit anyway?
   - *change the unit* — solve it per item, per batch, ahead of time, or not at all.
4. **Write the selection criteria** before choosing: what "good" means here, in three to five points taken from the goal and constraints.
5. **Converge.** Score candidates against the criteria. Combine strong parts when they are compatible. Say why the winner wins and what was given up.
6. **Prototype cheaply.** A sketch, an outline, twenty lines of code, one paragraph — enough to learn whether it works.
7. **For creative deliverables**, fix four things first: audience, single core idea, the feeling or action wanted, the hard format limits. Draft variants, pick with the criteria, then polish only the chosen one.
8. **Verify the hard constraints mechanically:** count the characters, time the script, check the dimensions, run the code. Originality never excuses a missed limit.

## Tools
- A scratch file for candidates and scores.
- Counting and measuring utilities for format limits.
- Quick prototypes in a sandbox.
- A fresh reader (reviewer agent or the user) for the shortlist.

## Outputs
- Goal restatement and constraint list.
- Candidate list with one line each.
- Criteria, the choice, and the reason.
- The prototype or draft, with constraint checks passed.

## Verification
- At least three candidates differed in mechanism or angle.
- Criteria were written before the choice.
- Every hard constraint was measured, not estimated.
- The result serves the goal as restated in step 1.

## Recovery
- **All candidates look alike:** you are anchored. Force a candidate that breaks one assumed constraint and one that uses a different medium or mechanism.
- **Nothing meets the constraints:** show the two closest candidates and which constraint each breaks; let the user choose what to relax.
- **Too many ideas, no decision:** tighten the criteria to three and choose; a decent option delivered beats a perfect one undecided.
- **The user dislikes the direction:** ask which criterion was wrong, update it, and re-run from step 3 rather than tweaking the rejected draft.
