import unittest
from decimal import Decimal

from aquaflow.meters.balance import Meter, volume, balance


class MeterVolumeTest(unittest.TestCase):
    def test_multiplier_scales_reading_delta(self):
        # 5 display units at a 10x multiplier represent 50 volume units
        m = Meter("i", Decimal("100"), Decimal("105"), Decimal("10"))
        self.assertEqual(volume(m), Decimal("50"))

    def test_fractional_multiplier_keeps_decimal_precision(self):
        m = Meter("i", Decimal("0.000"), Decimal("1.005"), Decimal("1.25"))
        self.assertEqual(volume(m), Decimal("1.25625"))

    def test_equal_opening_and_closing_is_zero_flow(self):
        m = Meter("flat", Decimal("42"), Decimal("42"), Decimal("10"))
        self.assertEqual(volume(m), Decimal("0"))

    def test_reversed_reading_is_rejected(self):
        m = Meter("back", Decimal("20"), Decimal("19"), Decimal("1"))
        with self.assertRaises(ValueError):
            volume(m)

    def test_non_positive_multiplier_is_rejected(self):
        with self.assertRaises(ValueError):
            volume(Meter("zero", Decimal("0"), Decimal("10"), Decimal("0")))
        with self.assertRaises(ValueError):
            volume(Meter("neg", Decimal("0"), Decimal("10"), Decimal("-1")))

    def test_reversed_reading_rejected_even_with_equal_lists_or_multiplier(self):
        good = [Meter("i", Decimal("0"), Decimal("10"), Decimal("1"))]
        bad = [Meter("o", Decimal("10"), Decimal("0"), Decimal("1"))]
        with self.assertRaises(ValueError):
            balance(good, bad, Decimal("0"))


class WaterBalanceTest(unittest.TestCase):
    def test_balance_uses_scaled_volumes(self):
        ins = [Meter("i", Decimal("0"), Decimal("20"), Decimal("2"))]   # 40 in
        outs = [Meter("o", Decimal("0"), Decimal("15"), Decimal("2"))]  # 30 out
        self.assertEqual(balance(ins, outs, Decimal("5")), Decimal("5"))

    def test_multiplier_not_one_was_previously_lost(self):
        # Without the multiplier this would be 20 - 15 - 1 = 4
        ins = [Meter("i", Decimal("0"), Decimal("20"), Decimal("3"))]   # 60
        outs = [Meter("o", Decimal("0"), Decimal("15"), Decimal("2"))]  # 30
        self.assertEqual(balance(ins, outs, Decimal("1")), Decimal("29"))

    def test_equal_readings_participate_as_zero(self):
        ins = [Meter("i", Decimal("8"), Decimal("8"), Decimal("100"))]
        outs = [Meter("o", Decimal("0"), Decimal("5"), Decimal("1"))]
        result = balance(ins, outs, Decimal("0"))
        self.assertEqual(result, Decimal("-5"))

    def test_negative_balance_is_flagged_not_clamped(self):
        ins = [Meter("i", Decimal("0"), Decimal("10"), Decimal("1"))]
        outs = [Meter("o", Decimal("0"), Decimal("15"), Decimal("1"))]
        result = balance(ins, outs, Decimal("0"))
        self.assertEqual(result, Decimal("-5"))
        self.assertTrue(result.needs_investigation)

    def test_non_negative_balance_is_not_flagged(self):
        ins = [Meter("i", Decimal("0"), Decimal("20"), Decimal("1"))]
        outs = [Meter("o", Decimal("0"), Decimal("15"), Decimal("1"))]
        result = balance(ins, outs, Decimal("1"))
        self.assertEqual(result, Decimal("4"))
        self.assertFalse(result.needs_investigation)

    def test_exact_zero_is_not_flagged(self):
        ins = [Meter("i", Decimal("0"), Decimal("10"), Decimal("1"))]
        outs = [Meter("o", Decimal("0"), Decimal("7"), Decimal("1"))]
        result = balance(ins, outs, Decimal("3"))
        self.assertEqual(result, Decimal("0"))
        self.assertFalse(result.needs_investigation)

    def test_decimal_precision_preserved_through_balance(self):
        ins = [Meter("i", Decimal("1.000"), Decimal("2.000"), Decimal("1.10"))]
        outs = [Meter("o", Decimal("0"), Decimal("0.25"), Decimal("0.40"))]
        result = balance(ins, outs, Decimal("0.00100"))
        # 1.100 - 0.100 - 0.001
        self.assertEqual(result, Decimal("0.99900"))
        self.assertIsInstance(result, Decimal)


if __name__ == "__main__":
    unittest.main()
