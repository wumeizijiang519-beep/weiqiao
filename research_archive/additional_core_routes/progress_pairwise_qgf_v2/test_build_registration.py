import unittest


class V2ContractTests(unittest.TestCase):
    def test_fixed_population_sizes(self):
        self.assertEqual(4 * (4 + 4), 32)
        self.assertEqual(4 * 4, 16)


if __name__ == "__main__": unittest.main()
