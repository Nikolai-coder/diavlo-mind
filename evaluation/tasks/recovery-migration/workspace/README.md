# Customer migration

One-off migration of the legacy customer export into the new JSON-lines format.

```
python tools/migrate.py data/customers.csv out/customers.jsonl --skip-errors
```

The tool was written for last year's export and has not been run since. `RULES.md` is the specification the output has to follow; where the tool and the rules disagree, the rules are right.
