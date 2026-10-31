import json
import unittest
from pathlib import Path


class ConfirmationSealTests(unittest.TestCase):
    def test_seal_contains_receipts_not_outcomes(self):
        path = Path(__file__).with_name("confirmation_seal_fixture.json")
        if not path.exists():
            self.skipTest("fixture is generated only after collection finalization")
        seal = json.loads(path.read_text())
        forbidden = {"branches", "progress", "success", "return", "reward"}
        for receipt in seal["receipts"]:
            self.assertFalse(forbidden.intersection(receipt))


if __name__ == "__main__":
    unittest.main()
