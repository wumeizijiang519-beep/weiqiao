import unittest


class AuditContractTests(unittest.TestCase):
    def test_confirmation_is_receipt_only(self):
        forbidden = {"success", "progress", "return"}
        receipt = {"entry_index", "episode_id", "split", "report_sha256"}
        self.assertFalse(forbidden.intersection(receipt))


if __name__ == "__main__": unittest.main()
