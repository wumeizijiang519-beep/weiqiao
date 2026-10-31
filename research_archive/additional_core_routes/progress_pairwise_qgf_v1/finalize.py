"""Combine the frozen pilot and remaining single-group results exactly once."""

import argparse
import hashlib
import json
from pathlib import Path

from final_metrics import qualify


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--remaining", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    expected = [entry["episode_id"] for entry in manifest["entries"]]
    rows = []
    receipts = []
    pilot_path = args.pilot / "REPORT.json"
    pilot = json.loads(pilot_path.read_text())
    if pilot.get("episode_id") != expected[0]:
        raise RuntimeError("Pilot is not frozen entry 0")
    rows.append(pilot)
    receipts.append({"entry_index": 0, "report_sha256": sha(pilot_path)})
    unavailable = []
    for index in range(1, 16):
        folder = args.remaining / f"entry_{index:02d}"
        report_path = folder / "REPORT.json"
        if report_path.exists():
            report = json.loads(report_path.read_text())
            if report.get("episode_id") != expected[index]:
                raise RuntimeError(f"Entry {index} episode identity changed")
            rows.append(report)
            receipts.append({"entry_index": index, "report_sha256": sha(report_path)})
        elif (folder / "FAILED.txt").exists():
            unavailable.append({"entry_index": index, "episode_id": expected[index],
                                "failure_sha256": sha(folder / "FAILED.txt")})
        else:
            raise RuntimeError(f"Entry {index} has no terminal receipt")
    if len({row["episode_id"] for row in rows}) != len(rows):
        raise RuntimeError("Duplicate physical episode in combined population")
    qualification = qualify(rows)
    if qualification["complete_groups"] < 12:
        qualification["status"] = "PROGRESS_PAIRWISE_INSUFFICIENT_COMPLETE_GROUPS"
    result = {
        **qualification,
        "unavailable_groups": unavailable,
        "population_episode_ids": expected,
        "report_receipts": receipts,
        "manifest_sha256": sha(args.manifest),
        "qgf_efficacy_claim": False,
        "results": rows,
    }
    args.output.mkdir(exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()


if __name__ == "__main__":
    main()
