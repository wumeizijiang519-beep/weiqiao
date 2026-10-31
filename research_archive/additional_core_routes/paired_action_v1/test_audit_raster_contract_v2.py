import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("audit_raster_contract_v2.py")
SPEC = importlib.util.spec_from_file_location("audit_raster_contract_v2", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_mismatch_locations():
    assert MODULE.mismatch_locations(["a", "b", "c"], ["a", "x", "c"]) == [1]


def test_mismatch_locations_length():
    assert MODULE.mismatch_locations(["a"], ["a", "b"]) == [1]
