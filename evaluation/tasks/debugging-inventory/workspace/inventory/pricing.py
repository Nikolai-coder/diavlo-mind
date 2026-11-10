"""Price calculations. All prices are integer cents."""


def apply_discount(price_cents, percent):
    """Return the price after a percentage discount, rounded half up to the nearest cent."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    if price_cents < 0:
        raise ValueError("price must not be negative")
    return int(price_cents * (100 - percent) / 100)


def line_total(price_cents, quantity, percent=0):
    """Total for a number of units with an optional discount per unit."""
    if quantity < 0:
        raise ValueError("quantity must not be negative")
    return apply_discount(price_cents, percent) * quantity
