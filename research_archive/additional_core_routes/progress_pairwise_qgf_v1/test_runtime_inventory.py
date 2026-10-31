import unittest

from runtime_inventory import jsonable, names


class RuntimeInventoryTest(unittest.TestCase):
    def test_jsonable_preserves_nested_predicates(self):
        value = (("In", "object", "target"), ("Close", "joint"))
        self.assertEqual(jsonable(value), [["In", "object", "target"], ["Close", "joint"]])

    def test_unknown_object_is_repr_only(self):
        class Token:
            def __repr__(self):
                return "TOKEN"
        self.assertEqual(jsonable(Token()), "TOKEN")

    def test_mujoco_joint_count_uses_njnt(self):
        class Model:
            njnt = 2

            @staticmethod
            def joint_id2name(index):
                return ("joint0", "joint1")[index]

        self.assertEqual(names(Model(), "joint"), ["joint0", "joint1"])

    def test_unknown_name_kind_fails_closed(self):
        with self.assertRaises(ValueError):
            names(object(), "camera")


if __name__ == "__main__":
    unittest.main()
