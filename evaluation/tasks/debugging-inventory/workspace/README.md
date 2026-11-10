# inventory

A small in-memory stock keeper.

- `inventory.models` — `Item` and `Inventory` (add, restock, remove, low-stock report, total value).
- `inventory.pricing` — price calculations. Prices are integer cents. Discounts round **half up** to the nearest cent.
- `inventory.report` — CSV export of an inventory.

Rules the code must follow:

- `Inventory.restock(sku, quantity)` adds `quantity` to what is already in stock.
- `Inventory.low_stock(threshold)` returns the items whose quantity is **at or below** the threshold, ordered by SKU.
- `export_csv(inventory)` returns CSV text with the header `sku,name,quantity,price_cents`, one line per item ordered by SKU, readable back with Python's `csv` module.

Run the tests with:

```
python -m unittest discover -s tests -v
```
