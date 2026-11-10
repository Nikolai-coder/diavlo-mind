# Migration rules

Input: `data/customers.csv`, UTF-8, with the header `id,name,email,signup_date,balance`. Fields may be quoted in the usual CSV way. Empty lines at the end of the file are ignored and not counted.

## Output 1 — `out/customers.jsonl`

One JSON object per accepted row, in input order, with exactly these keys:

| Key | Type | Rule |
|---|---|---|
| `id` | integer | The id as a number. |
| `name` | string | Leading and trailing whitespace removed; runs of whitespace inside the name replaced by one space. |
| `email` | string | Leading and trailing whitespace removed, then lower-cased. |
| `signup_date` | string | ISO form `YYYY-MM-DD`. The input uses either `YYYY-MM-DD` or `DD/MM/YYYY`. |
| `balance_cents` | integer | The balance in cents, exactly. The input is a decimal number with at most two decimal places, an optional leading `-`, and optional `,` thousands separators, for example `1,234.50` → `123450`. |

## Rejected rows

A row is rejected for the first reason in this list that applies:

1. `wrong_column_count` — the row does not have exactly 5 fields.
2. `missing_id` — the id is empty.
3. `invalid_id` — the id is not a positive integer.
4. `duplicate_id` — the id was already used by an earlier **accepted** row. The first one is kept.
5. `invalid_email` — after trimming, the email does not have exactly one `@` with a non-empty part before it and a part after it that contains a dot.
6. `invalid_date` — the date is in neither format, or is not a real calendar date.
7. `invalid_balance` — the balance is empty, not a number in the form above, or has more than two decimal places.

## Output 2 — `out/rejected.csv`

CSV with the header `line,reason,raw` and one row per rejected input row, in input order. `line` is the 1-based line number in `data/customers.csv` (the header is line 1). `reason` is one of the codes above. `raw` is the original line of text, without its line ending.

## Output 3 — `out/summary.json`

```json
{"total_rows": 0, "accepted": 0, "rejected": 0, "by_reason": {"invalid_email": 0}}
```

`total_rows` counts data rows (not the header, not the empty lines at the end). `accepted + rejected` must equal `total_rows`. `by_reason` contains only the reasons that occurred, with their counts.
