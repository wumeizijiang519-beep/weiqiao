import importlib.util
from pathlib import Path


PATH = Path(__file__).with_name("run_paired_diagnostic_v1.py")
SPEC = importlib.util.spec_from_file_location("paired", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_branch_order_is_deterministic_permutation():
    assert MODULE.branch_order("group-a") == MODULE.branch_order("group-a")
    assert sorted(MODULE.branch_order("group-a")) == [0, 1, 2, 3]


def test_different_groups_can_change_order():
    orders = {tuple(MODULE.branch_order(f"group-{index}")) for index in range(20)}
    assert len(orders) > 1
