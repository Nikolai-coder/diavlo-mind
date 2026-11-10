# Customer migration

One-off migration of the legacy customer export into the new JSON-lines format.

```
python tools/migrate.py data/customers.csv out
```

The tool writes `out/customers.jsonl`, `out/rejected.csv` and `out/summary.json` following `RULES.md`.
