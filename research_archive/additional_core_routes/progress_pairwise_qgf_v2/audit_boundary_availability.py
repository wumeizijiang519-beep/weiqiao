"""Audit reconstruction availability without reading branch outcomes."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


EXPECTED_FAILURE = "Reconstructed boundary policy input differs from archive"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(manifest, population):
    rows = []
    by_family = defaultdict(Counter)
    for index, entry in enumerate(manifest["entries"]):
        folder = population / f"entry_{index:02d}"
        report = folder / "REPORT.json"
        failure = folder / "FAILED.txt"
        if report.exists() and failure.exists():
            raise RuntimeError(f"entry {index} has conflicting terminal receipts")
        if report.exists():
            status, receipt = "complete", sha(report)
        elif failure.exists():
            text = failure.read_text(errors="replace")
            if EXPECTED_FAILURE not in text:
                raise RuntimeError(f"entry {index} has an unexpected failure")
            status, receipt = "boundary_mismatch", sha(failure)
        else:
            status, receipt = "pending", None
        family = entry["family"]
        split = entry["v2_split"]
        by_family[family][f"{split}_{status}"] += 1
        rows.append({"entry_index": index, "episode_id": entry["episode_id"],
                     "family": family, "split": split, "status": status,
                     "terminal_receipt_sha256": receipt})
    complete = sum(row["status"] == "complete" for row in rows)
    unavailable = sum(row["status"] == "boundary_mismatch" for row in rows)
    confirmation_complete = sum(row["status"] == "complete" and row["split"] == "confirmation"
                                for row in rows)
    confirmation_unavailable = sum(row["status"] == "boundary_mismatch"
                                   and row["split"] == "confirmation" for row in rows)
    return {
        "status": "BOUNDARY_AVAILABILITY_AUDIT",
        "complete": complete,
        "boundary_mismatch": unavailable,
        "pending": 32 - complete - unavailable,
        "confirmation_complete": confirmation_complete,
        "confirmation_boundary_mismatch": confirmation_unavailable,
        "overall_gate_still_reachable": unavailable <= 8,
        "confirmation_gate_still_reachable": confirmation_unavailable <= 4,
        "failure_mode": "EXACT_BOUNDARY_POLICY_OBSERVATION_MISMATCH",
        "branch_outcomes_read": False,
        "by_family": {key: dict(value) for key, value in sorted(by_family.items())},
        "receipts": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--population", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.manifest.read_text()), args.population)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
