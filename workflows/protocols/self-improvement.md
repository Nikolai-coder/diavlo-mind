# Self-improvement protocol — changing the framework from evidence

DIAVLO MIND improves by measured changes to its instructions, never by silent rewrites. Changing a prompt does not retrain a model; it changes what the model is asked to do. Every claim of improvement here means "the same model, with the changed instructions, scored better on the same tasks".

## When to use

- A task run with DIAVLO MIND failed, or succeeded with avoidable waste.
- A benchmark run shows a task or category where the framework does not help or hurts.
- Someone proposes a change to a rule, procedure, agent or prompt.

## The loop

### 1. Identify the observable failure
Write what happened, not why you think it happened: the task, the model and configuration, the expected result, the actual result, the evidence (failing check, transcript excerpt, token count). Record it with:

```
python scripts/dm_improve.py record --task <task-id> --model <model> --arm <arm> \
  --observed "<what happened>" --expected "<what should have happened>" --evidence <path>
```

### 2. Classify the cause
Exactly one primary category:

| Category | Meaning | Typical remedy |
|---|---|---|
| `missing_information` | The model lacked a fact or context it could not have found | Change the task input, the packet, or where the framework tells it to look |
| `inadequate_instructions` | The framework was silent, ambiguous or misleading for this situation | Edit a procedure, mode, agent or prompt |
| `insufficient_tools` | The environment could not do what the task needed | Change the adapter or tool setup; no prompt fixes this |
| `model_limitation` | Instructions and tools were adequate and the model still could not do it | Route the unit to a stronger model; record the limit; do not paper over it with more instructions |

To separate `inadequate_instructions` from `model_limitation`: give the model the missing instruction explicitly in the task and rerun. If it now succeeds reliably, the instructions were the problem.

### 3. Propose a targeted modification
One change, as small as possible, aimed at the classified cause. State the hypothesis: "Adding X to procedure P07 will stop the model from retrying the same command; it should raise success on error-recovery tasks without increasing tokens on others." Name the files to change.

### 4. Test it
Run the benchmark on the same model with and without the change, on **all** tasks, not only the one that failed (`evaluation/README.md`). Use at least three trials per task; more for small effects.

### 5. Compare
```
python evaluation/compare_runs.py <baseline-run-dir> <candidate-run-dir>
```
The comparison reports, per task and overall: success rate, requirement coverage, unresolved errors, overclaims, tokens and cost, with the paired difference.

### 6. Retain improvements supported by evidence
Accept a change only if all hold:

- the targeted metric improves on the targeted tasks;
- overall success rate does not drop;
- no other category gets worse beyond run-to-run noise;
- token cost does not rise by more than the gain justifies (state the trade explicitly).

### 7. Reject modifications that reduce overall performance
A change that fixes one task and harms the suite is rejected, and the rejection is recorded with its numbers so it is not proposed again.

```
python scripts/dm_improve.py decide --id <failure-id> --decision accepted|rejected \
  --baseline <run-dir> --candidate <run-dir> --note "<numbers and reason>"
```

## Versioning

- Every accepted change bumps `VERSION` (patch for wording, minor for a new or changed procedure, major for a change to the ten rules or the loop) and adds a `CHANGELOG.md` entry that cites the evidence.
- `evaluation/improvement/improvement-log.md` keeps the full record: failure, category, hypothesis, runs compared, decision.
- Prompt tiers in `prompts/system/` are rebuilt and checked with `scripts/build_prompts.py --check`.

## Protected core

The ten rules in `SKILL.md` are the fundamental operating rules. Their text is fingerprinted in `evaluation/improvement/core-rules.lock.json`, and `scripts/validate.py` fails when the text and the fingerprint differ. Changing them requires an explicit, recorded step:

```
python scripts/dm_improve.py approve-core-change --reason "<evidence and decision>"
```

This updates the lock and appends the reason to the improvement log. There is no way to change the core rules that passes validation without leaving that record.

## What this protocol does not claim

- It does not retrain or fine-tune any model.
- A gain measured on one model does not transfer automatically to another; re-measure per model.
- Small benchmark samples support small claims. Report the number of trials with every result.
