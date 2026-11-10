# export

Prints orders from a CSV file.

```
python export.py orders.csv
python export.py orders.csv --min-amount 100
python export.py orders.csv --since 2024-02-01
```

`--since YYYY-MM-DD` leaves out orders dated before that day; orders on that day are kept; it can be combined with `--min-amount`; an invalid date prints an error and exits with code 2.

Run the tests with `python -m unittest discover -s tests -v`.
