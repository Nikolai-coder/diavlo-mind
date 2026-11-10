import datetime
import io
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
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

    def test_since_filters_out_earlier_orders(self):
        _, lines = self.run_cli("--since", "2024-02-02")
        self.assertEqual([line.split()[1] for line in lines], ["acme", "hooli"])

    def test_since_keeps_orders_on_that_day(self):
        _, lines = self.run_cli("--since", "2024-02-01")
        self.assertEqual([line.split()[1] for line in lines], ["initech", "acme", "hooli"])
        self.assertTrue(lines[0].startswith("2024-02-01"))

    def test_since_before_all_rows_keeps_everything(self):
        _, lines = self.run_cli("--since", "2023-01-01")
        self.assertEqual(len(lines), 5)

    def test_since_after_all_rows_prints_nothing(self):
        code, lines = self.run_cli("--since", "2025-01-01")
        self.assertEqual(code, 0)
        self.assertEqual(lines, [])

    def test_since_combines_with_min_amount(self):
        _, lines = self.run_cli("--since", "2024-02-01", "--min-amount", "100")
        self.assertEqual([line.split()[1] for line in lines], ["initech"])

    def test_select_since_parameter(self):
        rows = export.select(export.load(DATA), since=datetime.date(2024, 3, 2))
        self.assertEqual([row["customer"] for row in rows], ["hooli"])

    def test_invalid_since_exits_with_code_2(self):
        for value in ["not-a-date", "2024-02-30", "2024-13-01", "20240201", "2024-2-1", "01-02-2024", ""]:
            with self.subTest(value=value):
                stdout_buf = io.StringIO()
                stderr_buf = io.StringIO()
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    with self.assertRaises(SystemExit) as ctx:
                        export.main([DATA, "--since", value])
                self.assertEqual(ctx.exception.code, 2)
                stderr_text = stderr_buf.getvalue()
                self.assertIn("--since", stderr_text)
                self.assertIn("YYYY-MM-DD", stderr_text)
                self.assertEqual(stdout_buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
