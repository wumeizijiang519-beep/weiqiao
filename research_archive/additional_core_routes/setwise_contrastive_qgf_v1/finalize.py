"""Finalize the frozen 24-group Setwise-Contrastive population."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


TIE_TOLERANCE = 1e-6


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def split_gate(rows, split_by_episode):
    families = defaultdict(int)
    groups = 0
    for row in rows:
        if split_by_episode[row["episode_id"]] not in ("development", "confirmation"):
            raise RuntimeError("Unknown split")
        values = [float(branch["progress_at_32"]["value"]) for branch in row["branches"]]
        if max(values) - min(values) > TIE_TOLERANCE:
            families[row["family"]] += 1
        groups += 1
    return {
        "complete_groups": groups,
        "non_tie_families": sorted(families),
        "non_tie_groups_by_family": dict(sorted(families.items())),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--remaining", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    expected = [entry["episode_id"] for entry in manifest["entries"]]
    split_by_episode = {entry["episode_id"]: entry["setwise_split"] for entry in manifest["entries"]}
    unavailable_path = args.remaining / "UNAVAILABLE_ENTRY_INDICES"
    unavailable = [] if not unavailable_path.exists() else [int(value) for value in unavailable_path.read_text().split()]
    rows = []
    receipts = []
    for index in range(24):
        path = args.pilot / "REPORT.json" if index == 0 else args.remaining / f"entry_{index:02d}" / "REPORT.json"
        if not path.exists():
            if index not in unavailable:
                raise RuntimeError(f"Entry {index} lacks a terminal receipt")
            continue
        report = json.loads(path.read_text())
        if report.get("episode_id") != expected[index]:
            raise RuntimeError(f"Entry {index} identity changed")
        rows.append(report)
        receipts.append({"entry_index": index, "report_sha256": sha(path)})
    if len({row["episode_id"] for row in rows}) != len(rows):
        raise RuntimeError("Duplicate completed group")
    split_rows = {
        split: [row for row in rows if split_by_episode[row["episode_id"]] == split]
        for split in ("development", "confirmation")
    }
    gates = {split: split_gate(values, split_by_episode) for split, values in split_rows.items()}
    admitted = all(gates[split]["complete_groups"] >= 12 and len(gates[split]["non_tie_families"]) >= 2
                   for split in gates)
    result = {
        "status": "SETWISE_CONTRASTIVE_DATA_ADMIT" if admitted else "SETWISE_CONTRASTIVE_DATA_INSUFFICIENT",
        "complete_groups": len(rows),
        "unavailable_indices": sorted(unavailable),
        "split_gates": gates,
        "tie_tolerance": TIE_TOLERANCE,
        "manifest_sha256": sha(args.manifest),
        "report_receipts": receipts,
        "qgf_efficacy_claim": False,
        "results": rows,
    }
    args.output.mkdir(exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()


if __name__ == "__main__":
    main()
