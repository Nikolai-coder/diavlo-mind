# Contributing

Contributions are welcome: corrections, adapters for more environments, benchmark tasks and benchmark results from models that were not measured here.

## Before you open a pull request

```bash
python scripts/build_prompts.py            # re-sync the prompt tiers if SKILL.md or any procedure changed
python scripts/validate.py                 # must report 0 errors
python -m unittest discover -s tests       # must pass
python evaluation/selftest.py              # must pass if you touched evaluation/
```

The same four commands run in CI on Linux, macOS and Windows.

## What kind of change is it?

| Change | Requirements |
|---|---|
| Typo, clearer wording, broken link | The four commands above |
| New or corrected adapter | State at the top what you executed and what you only read in documentation; link the primary sources |
| New procedure, role or template | Follow the section structure of the existing files; add the routing row in `SKILL.md`; explain which failure it prevents |
| New benchmark task | `task.json`, prompt, seeded workspace, `checks/check.py`, `reference/`; `evaluation/selftest.py` must show the checks reject empty work and accept the reference |
| Change to how the framework instructs a model | Benchmark evidence: run the suite before and after on the same model with at least three trials, attach `compare_runs.py` output, and record it with `scripts/dm_improve.py` |
| Change to the ten rules | All of the above, plus `python scripts/dm_improve.py approve-core-change --reason "…"` and a major version bump |

## Rules for instruction text

- Describe actions a model can perform and an outsider can observe. "Run the narrowest test that could fail" is an instruction; "be careful" is not.
- No capability claims. Do not write that the framework makes a model smarter, or equal to another model. Write what was measured, on which model, with how many trials.
- No request for private reasoning. Ask for decisions, evidence and alternatives considered, in a few lines.
- Shorter is better. Every added sentence is paid for in tokens on every task, by every user.
- Do not describe features of a product you have not verified. Mark what you read in documentation as such, with the date.

## Reporting benchmark results

Use the "Benchmark result" issue template. Include the model, the runner, the number of trials, the framework version, and the `SUMMARY.md` produced by `evaluation/score.py`. Results that show no effect or a negative effect are as useful as positive ones.

## Reporting a failure of the framework

Use the "Framework failure" issue template: what the model did, what it should have done, the transcript or the failing check, and the model and environment. If you can, say which cause category from `workflows/protocols/self-improvement.md` you think applies.

## Licence

By contributing you agree that your contribution is released under the MIT licence of this repository.
