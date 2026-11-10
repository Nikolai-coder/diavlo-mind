This directory contains a small Python package, `inventory`, with a test suite in `tests/`.

One test is failing, and users have reported the problems listed in `BUGS.md`. Fix every reported problem. For each one, add a regression test that fails with the old code and passes with your fix.

Keep the changes minimal: do not rewrite the modules, do not change the public API (function and method names, parameters and return types stay as they are), and do not remove or weaken the existing tests.

When you are done, `python -m unittest discover -s tests -v` must pass.

End your final message with exactly one line: `STATUS: COMPLETE` or `STATUS: INCOMPLETE - <what is missing>`.
