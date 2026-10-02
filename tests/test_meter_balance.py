import unittest
from decimal import Decimal

from aquaflow.api import AquaFlowService
from aquaflow.meters.balance import Meter, balance, volume


D = Decimal


class MeterBalanceTests(unittest.TestCase):
    def test_multiplier_scales_volume(self):
        # register delta 20 at multiplier 3 represents 60 actual units
        m = Meter("i", D("0"), D("20"), D("3"))
        self.assertEqual(volume(m), D("60"))

    def test_balance_uses_multiplier_for_inputs_and_outputs(self):
        ins = [Meter("i", D("0"), D("20"), D("3"))]   # 60 in
        outs = [Meter("o", D("0"), D("10"), D("4"))]  # 40 out
        self.assertEqual(balance(ins, outs, D("5")), D("15"))

    def test_input_under_counted_without_fix_regression(self):
        # Before the fix an input multiplier of 10 was silently dropped.
        ins = [Meter("i", D("0"), D("2"), D("10"))]  # 20 in
        outs = [Meter("o", D("0"), D("15"), D("1"))]
        self.assertEqual(balance(ins, outs, D("0")), D("5"))

    def test_decimal_precision_preserved(self):
        ins = [Meter("i", D("100.000"), D("100.125"), D("1.2"))]
        # 0.125 * 1.2 = 0.150 exactly in Decimal
        self.assertEqual(volume(ins[0]), D("0.150"))
        self.assertEqual(balance(ins, [], D("0.05")), D("0.100"))

    def test_equal_open_close_readings_are_zero(self):
        m = Meter("flat", D("123.45"), D("123.45"), D("7"))
        self.assertEqual(volume(m), D("0"))
        self.assertEqual(balance([m], [m], D("0")), D("0"))

    def test_reversed_reading_rejected(self):
        with self.assertRaises(ValueError):
            volume(Meter("bad", D("50"), D("49"), D("1")))
        with self.assertRaises(ValueError):
            balance([Meter("bad", D("50"), D("49"), D("1"))], [], D("0"))

    def test_illegal_multiplier_rejected(self):
        for mult in (D("0"), D("-1")):
            with self.assertRaises(ValueError):
                volume(Meter("bad", D("0"), D("10"), mult))

    def test_negative_balance_is_returned_not_clamped(self):
        ins = [Meter("i", D("0"), D("5"), D("1"))]
        outs = [Meter("o", D("0"), D("9"), D("1"))]
        # 5 - 9 - 1 = -5, must stay negative
        self.assertEqual(balance(ins, outs, D("1")), D("-5"))

    def test_known_loss_subtracted(self):
        ins = [Meter("i", D("0"), D("100"), D("1"))]
        self.assertEqual(balance(ins, [], D("30")), D("70"))

    def test_service_api_keeps_decimal_result(self):
        ins = [Meter("i", D("0"), D("20"), D("3"))]
        outs = [Meter("o", D("0"), D("15"), D("1"))]
        result = AquaFlowService().water_balance(ins, outs, D("10"))
        self.assertEqual(result, D("35"))
        self.assertIsInstance(result, Decimal)


class MeterBalanceWorkflowTests(unittest.TestCase):
    def run_workflow(self, payload):
        return AquaFlowService().run_workflow("meter_balance", payload)

    def test_workflow_applies_input_multiplier(self):
        payload = {
            "inputs": [{"id": "i", "opening": 0, "closing": 2, "multiplier": 10}],
            "outputs": [{"id": "o", "opening": 0, "closing": 15, "multiplier": 1}],
            "known_loss": 0,
        }
        r = self.run_workflow(payload)
        self.assertEqual(r["value"], D("5"))
        self.assertEqual(r["decision"], "reconcile")
        self.assertFalse(r["needs_investigation"])

    def test_workflow_applies_output_multiplier(self):
        payload = {
            "inputs": [{"id": "i", "opening": 0, "closing": 100, "multiplier": 1}],
            "outputs": [{"id": "o", "opening": 0, "closing": 20, "multiplier": 4}],
            "known_loss": 0,
        }
        r = self.run_workflow(payload)
        self.assertEqual(r["value"], D("20"))

    def test_workflow_equal_readings_reconcile(self):
        payload = {
            "inputs": [{"id": "i", "opening": 5, "closing": 5, "multiplier": 3}],
            "outputs": [{"id": "o", "opening": 5, "closing": 5, "multiplier": 3}],
            "known_loss": 0,
        }
        r = self.run_workflow(payload)
        self.assertEqual(r["value"], D("0"))
        self.assertEqual(r["decision"], "reconcile")

    def test_workflow_negative_balance_flagged_for_investigation(self):
        payload = {
            "inputs": [{"id": "i", "opening": 0, "closing": 5, "multiplier": 1}],
            "outputs": [{"id": "o", "opening": 0, "closing": 9, "multiplier": 1}],
            "known_loss": 1,
        }
        r = self.run_workflow(payload)
        # value stays negative (no silent clamp) and is explicitly flagged
        self.assertEqual(r["value"], D("-5"))
        self.assertEqual(r["decision"], "investigate")
        self.assertTrue(r["needs_investigation"])

    def test_workflow_reversed_reading_rejected(self):
        payload = {
            "inputs": [{"id": "i", "opening": 50, "closing": 49, "multiplier": 1}],
            "outputs": [],
            "known_loss": 0,
        }
        with self.assertRaises(ValueError):
            self.run_workflow(payload)

    def test_workflow_missing_multiplier_defaults_to_one(self):
        payload = {
            "inputs": [{"id": "i", "opening": 0, "closing": 12}],
            "outputs": [{"id": "o", "opening": 0, "closing": 10}],
            "known_loss": 2,
        }
        r = self.run_workflow(payload)
        self.assertEqual(r["value"], D("0"))


if __name__ == "__main__":
    unittest.main()
