Create `duration.py` in this directory with two functions, plus a test file.

`parse_duration(text)` turns a human-readable duration into a whole number of seconds. Inputs look like `1h30m`, `2d 4h`, `45s` or `1w2d3h4m5s`. The units are `w` (weeks), `d` (days), `h` (hours), `m` (minutes) and `s` (seconds). Units must appear in descending order and each unit may appear at most once. Whitespace around the string and between components is allowed; whitespace between a number and its unit is not. Unit letters are case-insensitive. A string that is just an integer, such as `90`, means seconds; otherwise every component needs a unit. Numbers are non-negative integers with no sign and no decimal point; leading zeros are fine. The empty string, a string of only whitespace, unknown units, repeated units, units out of order, a missing number, signs and decimals must raise `ValueError`, and the error message must contain the offending input text. Passing something that is not a `str` must raise `TypeError`.

`format_duration(seconds)` is the inverse. It returns the canonical compact form: largest units first, zero components omitted, no spaces — `5400` gives `1h30m` and `0` gives `0s`. It accepts only non-negative `int` values: a negative number raises `ValueError`, and anything that is not an `int` (including `bool` and `float`) raises `TypeError`.

For every valid input `x`, `parse_duration(format_duration(parse_duration(x)))` must equal `parse_duration(x)`.

Also write `test_duration.py` using `unittest`, with at least 12 test methods that pass when run with `python -m unittest test_duration -v`.

Use only the Python standard library. Do not create any files other than `duration.py` and `test_duration.py`.

End your final message with exactly one line: `STATUS: COMPLETE` or `STATUS: INCOMPLETE - <what is missing>`.
