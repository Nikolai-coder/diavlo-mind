# export

Prints orders from a CSV file.

```
python export.py orders.csv
python export.py orders.csv --min-amount 100
python export.py orders.csv --since 2024-02-01
```

Options:

- `--min-amount AMOUNT` leaves out orders below this amount.
- `--since YYYY-MM-DD` leaves out orders dated before this day. Orders dated on that day are kept. An invalid date (for example `2024-02-30` or `02/01/2024`) prints an error message and exits with code 2.

Run the tests with `python -m unittest discover -s tests -v`.
