## What changes

<!-- One or two sentences. Name the files that matter. -->

## Why

<!-- The failure or gap this addresses. Link the issue if there is one. -->

## Kind of change

- [ ] Wording, typo or broken link
- [ ] Adapter (state below what you executed and what you only read in documentation)
- [ ] New procedure, role, template or benchmark task
- [ ] Change to how the framework instructs a model (benchmark evidence below)
- [ ] Change to the ten rules or the loop (major version, `dm_improve.py approve-core-change`)
- [ ] Script, test or tooling

## Checks run locally

- [ ] `python scripts/build_prompts.py --check`
- [ ] `python scripts/validate.py` reports 0 errors
- [ ] `python -m unittest discover -s tests` passes
- [ ] `python evaluation/selftest.py` passes (when `evaluation/` changed)

## Evidence

<!-- For instruction changes: model, runner, trials per task, and the compare_runs.py output before and after.
     For adapters: the commands you ran and their output, plus links to the primary sources.
     Write what was measured. Do not claim an improvement that was not measured. -->

## Not verified

<!-- What you could not test (platforms, hosts, providers). "Nothing" is a valid answer. -->
