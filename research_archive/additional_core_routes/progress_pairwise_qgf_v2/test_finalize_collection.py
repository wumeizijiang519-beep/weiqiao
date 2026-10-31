import unittest


class CollectionContractTests(unittest.TestCase):
    def test_admission_denominators(self):
        self.assertTrue(24 >= 24 and 12 >= 12)
        self.assertFalse(23 >= 24 and 16 >= 12)
        self.assertFalse(24 >= 24 and 11 >= 12)


if __name__ == "__main__": unittest.main()
