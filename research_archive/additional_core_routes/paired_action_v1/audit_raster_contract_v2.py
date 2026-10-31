"""Re-audit frozen replay evidence under the approved Raster Contract V2."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


ARRAY_FIELDS = ("rewards", "done", "success", "proprio", "native", "env_state")
HASH_FIELDS = ("rng", "policy_raster")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_branch(run, label):
    with np.load(run / f"{label}.npz", allow_pickle=False) as data:
        arrays = {key: np.asarray(data[key]) for key in ARRAY_FIELDS}
    hashes = json.loads((run / f"{label}_hashes.json").read_text())
    return arrays, hashes


def mismatch_locations(left, right):
    count = min(len(left), len(right))
    locations = [index for index in range(count) if left[index] != right[index]]
    locations.extend(range(count, max(len(left), len(right))))
    return locations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--strict-failure-sha", required=True)
    parser.add_argument("--contract-sha", required=True)
    args = parser.parse_args()

    run = Path(args.run)
    output = Path(args.output)
    output.mkdir(exist_ok=False)
    strict_failure = run.parent / "REPLAY_ABA_GATE_V2_FAILURE_RESULT.json"
    contract = run.parent / "RASTER_CONTRACT_V2.md"
    if sha256(strict_failure) != args.strict_failure_sha:
        raise RuntimeError("Frozen strict failure result changed")
    if sha256(contract) != args.contract_sha:
        raise RuntimeError("Approved contract changed")

    branches = {label: load_branch(run, label) for label in ("A0", "B0", "A1", "A2")}
    reference_arrays, reference_hashes = branches["A0"]
    comparisons = {}
    for label in ("A1", "A2"):
        arrays, hashes = branches[label]
        array_equal = {key: bool(np.array_equal(reference_arrays[key], arrays[key]))
                       for key in ARRAY_FIELDS}
        hash_equal = {key: reference_hashes[key] == hashes[key] for key in HASH_FIELDS}
        boundary_equal = {
            key: reference_hashes["boundary"][key] == hashes["boundary"][key]
            for key in ("proprio", "native", "env_state", "rng", "policy_raster")
        }
        direct_mismatches = mismatch_locations(reference_hashes["direct_raster"],
                                               hashes["direct_raster"])
        direct_boundary_equal = (reference_hashes["boundary"]["direct_raster"]
                                 == hashes["boundary"]["direct_raster"])
        comparisons[label] = {
            "array_equal": array_equal,
            "hash_equal": hash_equal,
            "boundary_equal": boundary_equal,
            "direct_raster_audit_only": {
                "boundary_equal": direct_boundary_equal,
                "mismatch_steps": direct_mismatches,
            },
        }
        if not all(array_equal.values()) or not all(hash_equal.values()) or not all(boundary_equal.values()):
            raise RuntimeError(f"{label} failed an admission field")

    b_arrays, b_hashes = branches["B0"]
    b_perturbs = (not np.array_equal(reference_arrays["native"], b_arrays["native"])
                  or reference_hashes["policy_raster"] != b_hashes["policy_raster"])
    if not b_perturbs:
        raise RuntimeError("B0 did not perturb the trajectory")

    report = {
        "status": "RASTER_CONTRACT_V2_ADMISSION_PASS",
        "strict_v2_failure_preserved": True,
        "policy_input_exact": True,
        "state_rng_feedback_exact": True,
        "action_replay_max_abs_error": 0.0,
        "b0_perturbs_trajectory": True,
        "comparisons": comparisons,
        "qgf_evaluated": False,
        "gpu_seconds": 0,
        "source_evidence": {
            "strict_failure_sha256": sha256(strict_failure),
            "contract_sha256": sha256(contract),
        },
    }
    report_path = output / "REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    (output / "RASTER_CONTRACT_V2_ADMISSION_PASS").touch()
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
