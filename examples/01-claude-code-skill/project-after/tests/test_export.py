import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
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

    def test_since_leaves_out_orders_before_the_day(self):
        code, lines = self.run_cli("--since", "2024-02-01")
        self.assertEqual(code, 0)
        # orders on 2024-01-05 and 2024-01-31 are dropped
        self.assertEqual([line.split()[0] for line in lines],
                         ["2024-02-01", "2024-02-14", "2024-03-02"])

    def test_since_keeps_orders_on_that_day(self):
        _, lines = self.run_cli("--since", "2024-02-01")
        self.assertTrue(lines[0].startswith("2024-02-01"))
        self.assertIn("initech", lines[0])

    def test_since_on_first_day_keeps_every_row(self):
        _, lines = self.run_cli("--since", "2024-01-05")
        self.assertEqual(len(lines), 5)

    def test_since_just_after_first_day_drops_only_that_day(self):
        _, lines = self.run_cli("--since", "2024-01-06")
        self.assertEqual(len(lines), 4)
        self.assertNotIn("2024-01-05", "\n".join(lines))

    def test_since_after_last_day_prints_nothing(self):
        code, lines = self.run_cli("--since", "2024-03-03")
        self.assertEqual(code, 0)
        self.assertEqual(lines, [])

    def test_since_combines_with_min_amount(self):
        _, lines = self.run_cli("--since", "2024-02-01", "--min-amount", "100")
        self.assertEqual([line.split()[1] for line in lines], ["initech"])

    def test_select_with_since_filters_by_date(self):
        rows = export.select(export.load(DATA), since=export.parse_since("2024-02-14"))
        self.assertEqual([row["customer"] for row in rows], ["acme", "hooli"])

    def test_invalid_since_exits_with_code_2_and_message(self):
        for bad in ["2024-13-01", "2024-02-30", "not-a-date", "2024/01/01", ""]:
            with self.subTest(value=bad):
                stdout, stderr = io.StringIO(), io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as ctx:
                        export.main([DATA, "--since", bad])
                self.assertEqual(ctx.exception.code, 2)
                self.assertIn("invalid date", stderr.getvalue())
                self.assertIn("YYYY-MM-DD", stderr.getvalue())
                self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
