import unittest

from inventory import Inventory, Item, apply_discount, export_csv
from inventory.pricing import line_total


def stocked():
    inventory = Inventory({})
    inventory.add(Item("A-100", "Washer", 5, 25))
    inventory.add(Item("B-200", "Bolt", 40, 110))
    return inventory


class InventoryTests(unittest.TestCase):
    def test_add_and_total_value(self):
        self.assertEqual(stocked().total_value(), 5 * 25 + 40 * 110)

    def test_add_rejects_duplicate_sku(self):
        inventory = stocked()
        with self.assertRaises(ValueError):
            inventory.add(Item("A-100", "Other", 1, 1))

    def test_restock_adds_to_existing_quantity(self):
        inventory = stocked()
        self.assertEqual(inventory.restock("A-100", 3), 8)
        self.assertEqual(inventory.items["A-100"].quantity, 8)

    def test_restock_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            stocked().restock("A-100", 0)

    def test_remove(self):
        inventory = stocked()
        self.assertEqual(inventory.remove("B-200", 15), 25)
        with self.assertRaises(ValueError):
            inventory.remove("B-200", 26)

    def test_unknown_sku(self):
        with self.assertRaises(KeyError):
            stocked().restock("Z-999", 1)

    def test_low_stock_below_threshold(self):
        self.assertEqual([item.sku for item in stocked().low_stock(10)], ["A-100"])


class PricingTests(unittest.TestCase):
    def test_discount_whole_cents(self):
        self.assertEqual(apply_discount(1000, 25), 750)
        self.assertEqual(apply_discount(1000, 0), 1000)
        self.assertEqual(apply_discount(1000, 100), 0)

    def test_discount_rejects_bad_percent(self):
        with self.assertRaises(ValueError):
            apply_discount(1000, 101)

    def test_line_total(self):
        self.assertEqual(line_total(200, 3, 50), 300)


class ReportTests(unittest.TestCase):
    def test_export_simple(self):
        self.assertEqual(export_csv(stocked()),
                         "sku,name,quantity,price_cents\nA-100,Washer,5,25\nB-200,Bolt,40,110\n")


if __name__ == "__main__":
    unittest.main()
