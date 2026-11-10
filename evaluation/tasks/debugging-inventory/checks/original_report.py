"""Reports built from an inventory."""

HEADER = "sku,name,quantity,price_cents"


def export_csv(inventory):
    """Return the inventory as CSV text, one line per item ordered by SKU."""
    lines = [HEADER]
    for sku in sorted(inventory.items):
        item = inventory.items[sku]
        lines.append(",".join([item.sku, item.name, str(item.quantity), str(item.price_cents)]))
    return "\n".join(lines) + "\n"
