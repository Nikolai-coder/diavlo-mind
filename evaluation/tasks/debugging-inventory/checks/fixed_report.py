"""Reports built from an inventory."""
import csv
import io

HEADER = "sku,name,quantity,price_cents"


def export_csv(inventory):
    """Return the inventory as CSV text, one line per item ordered by SKU."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER.split(","))
    for sku in sorted(inventory.items):
        item = inventory.items[sku]
        writer.writerow([item.sku, item.name, item.quantity, item.price_cents])
    return buffer.getvalue()
