Mode: STANDARD (small change, clear criteria, few files).

Result: `--since YYYY-MM-DD` is added to `export.py`, with tests in `tests/test_export.py` and docs in `README.md`. The changed files are in `<workspace>/` (`export.py`, `tests/test_export.py`, `README.md`). The project is not a git repository, so I did not commit.

Status: DONE

Evidence:

| Req | Status | Evidence |
|---|---|---|
| R1 `--since` option | met — VERIFIED | `python3 export.py orders.csv --since 2024-02-01` prints the 3 orders dated on or after that day, exit 0 |
| R2 drop earlier, keep same day | met — VERIFIED | Tests `test_since_leaves_out_orders_before_the_day`, `test_since_keeps_orders_on_that_day`, `test_since_on_first_day_keeps_every_row`, `test_since_just_after_first_day_drops_only_that_day` pass |
| R3 invalid date → message, exit 2 | met — VERIFIED | `python3 export.py orders.csv --since 2024-02-30` → `export.py: error: argument --since: invalid date '2024-02-30', expected YYYY-MM-DD`, exit=2. Test `test_invalid_since_exits_with_code_2_and_message` covers 5 bad inputs |
| R4 README documents option | met — VERIFIED | README gains a `--since` example and an options list (read back in the edit) |
| R5 existing tests pass | met — VERIFIED | Baseline 4 passed before; `python3 -m unittest discover -s tests -v` → Ran 12 tests, OK |
| R6 tests for new behaviour | met — VERIFIED | 8 new tests, including the combination with `--min-amount` and `select(since=...)` |

Decisions:
- Used argparse's `type=` with `ArgumentTypeError`. argparse then prints the message and exits with code 2 itself, so no custom exit logic was needed. The alternative was a manual check in `main()`, which would duplicate argparse's behaviour.
- The date is parsed with `datetime.strptime(..., "%Y-%m-%d")`. This is simple and rejects impossible dates like `2024-02-30`.
- I also documented the existing `--min-amount` option in the README, since the options list was new. That is a small addition beyond the request.

Not done / not verified:
- A malformed date inside `orders.csv` (for example `2024/01/05`) raises a `ValueError` traceback when `--since` is used. Without `--since`, the row dates are never parsed, so the default behaviour is unchanged. I did not add handling for bad row data, since the request covers only the option's own input.
- `strptime` is slightly lenient: `2024-1-5` is accepted as a valid `--since` value. This is not a strict YYYY-MM-DD check.

Assumptions: the existing test runner and Python 3.13 are the ones the project uses (taken from the README command and the installed interpreter).

Next step: decide whether you want strict `YYYY-MM-DD` matching (a regex check in `parse_since`) and whether malformed row dates should produce a clear error instead of a traceback.
