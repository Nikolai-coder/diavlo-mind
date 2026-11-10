"""Items and the inventory that holds them."""
from dataclasses import dataclass


@dataclass
class Item:
    sku: str
    name: str
    quantity: int
    price_cents: int


class Inventory:
    """Keeps items by SKU."""

    def __init__(self, items=None):
        self.items = items if items is not None else {}

    def add(self, item):
        """Add a new item. Raises ValueError if the SKU already exists."""
        if item.sku in self.items:
            raise ValueError(f"duplicate sku: {item.sku}")
        if item.quantity < 0:
            raise ValueError("quantity must not be negative")
        self.items[item.sku] = item

    def restock(self, sku, quantity):
        """Receive more units of an existing item and return the new quantity."""
        if quantity <= 0:
            raise ValueError("restock quantity must be positive")
        item = self._get(sku)
        item.quantity += quantity
        return item.quantity

    def remove(self, sku, quantity):
        """Take units out of stock and return the new quantity."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        item = self._get(sku)
        if quantity > item.quantity:
            raise ValueError(f"only {item.quantity} units of {sku} in stock")
        item.quantity -= quantity
        return item.quantity

    def low_stock(self, threshold):
        """Items at or below the threshold, ordered by SKU."""
        low = [item for item in self.items.values() if item.quantity < threshold]
        return sorted(low, key=lambda item: item.sku)

    def total_value(self):
        """Value of everything in stock, in cents."""
        return sum(item.quantity * item.price_cents for item in self.items.values())

    def _get(self, sku):
        try:
            return self.items[sku]
        except KeyError:
            raise KeyError(f"unknown sku: {sku}") from None
