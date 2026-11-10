import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import export  # noqa: E402

DATA = str(Path(__file__).resolve().parent.parent / "orders.csv")


class ExportTests(unittest.TestCase):
    def run_cli(self, *args):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = export.main([DATA, *args])
        return code, buffer.getvalue().splitlines()

    def test_prints_every_row_by_default(self):
        code, lines = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), 5)

    def test_min_amount_filters(self):
        _, lines = self.run_cli("--min-amount", "100")
        self.assertEqual([line.split()[1] for line in lines], ["acme", "initech"])

    def test_select_keeps_input_order(self):
        rows = export.select(export.load(DATA))
        self.assertEqual([row["customer"] for row in rows], ["acme", "globex", "initech", "acme", "hooli"])

    def test_amount_is_formatted_with_two_decimals(self):
        _, lines = self.run_cli()
        self.assertTrue(lines[1].endswith("40.50"))


if __name__ == "__main__":
    unittest.main()
