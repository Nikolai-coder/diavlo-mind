import unittest

from duration import format_duration, parse_duration


class ParseTests(unittest.TestCase):
    def test_single_units(self):
        self.assertEqual(parse_duration("45s"), 45)
        self.assertEqual(parse_duration("2m"), 120)
        self.assertEqual(parse_duration("1h"), 3600)
        self.assertEqual(parse_duration("1d"), 86400)
        self.assertEqual(parse_duration("1w"), 604800)

    def test_combination(self):
        self.assertEqual(parse_duration("1h30m"), 5400)
        self.assertEqual(parse_duration("1w2d3h4m5s"), 788645)

    def test_whitespace_between_components_and_around(self):
        self.assertEqual(parse_duration("  2d 4h "), 2 * 86400 + 4 * 3600)

    def test_whitespace_inside_component_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_duration("1 h")

    def test_case_insensitive(self):
        self.assertEqual(parse_duration("1H30M"), 5400)

    def test_bare_integer_is_seconds(self):
        self.assertEqual(parse_duration("90"), 90)
        self.assertEqual(parse_duration(" 090 "), 90)

    def test_trailing_number_without_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_duration("1h30")

    def test_leading_zeros(self):
        self.assertEqual(parse_duration("01h05m"), 3900)

    def test_order_and_repeats(self):
        for bad in ("1m1h", "1d1d", "1s1w"):
            with self.assertRaises(ValueError):
                parse_duration(bad)

    def test_invalid_inputs_name_the_input(self):
        for bad in ("", "   ", "1x", "h", "-1h", "+1h", "1.5h", "abc"):
            with self.assertRaises(ValueError) as caught:
                parse_duration(bad)
            self.assertIn(bad, str(caught.exception))

    def test_non_string_is_a_type_error(self):
        for bad in (90, None, b"1h", 1.5):
            with self.assertRaises(TypeError):
                parse_duration(bad)


class FormatTests(unittest.TestCase):
    def test_canonical_form(self):
        self.assertEqual(format_duration(0), "0s")
        self.assertEqual(format_duration(5400), "1h30m")
        self.assertEqual(format_duration(3601), "1h1s")
        self.assertEqual(format_duration(694861), "1w1d1h1m1s")

    def test_rejects_negative(self):
        with self.assertRaises(ValueError):
            format_duration(-1)

    def test_rejects_non_int(self):
        for bad in (1.0, True, "60", None):
            with self.assertRaises(TypeError):
                format_duration(bad)

    def test_round_trip(self):
        for text in ("1h30m", "90", "2d 4h", "0s", "100000h", "59s", "1W"):
            seconds = parse_duration(text)
            self.assertEqual(parse_duration(format_duration(seconds)), seconds)


if __name__ == "__main__":
    unittest.main()
