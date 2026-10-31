"""Combine the fixed pilot, ten clean groups, and fixed entry-11 resume."""

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
    parser.add_argument("--resume", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    expected = [entry["episode_id"] for entry in manifest["entries"]]
    sources = [(0, args.pilot / "REPORT.json")]
    sources.extend(
        (index, args.remaining / f"entry_{index:02d}" / "REPORT.json")
        for index in range(1, 11)
    )
    sources.append((11, args.resume / "REPORT.json"))
    rows = []
    receipts = []
    for index, report_path in sources:
        report = json.loads(report_path.read_text())
        if report.get("episode_id") != expected[index]:
            raise RuntimeError(f"Entry {index} identity changed")
        rows.append(report)
        receipts.append({"entry_index": index, "report_sha256": sha(report_path)})
    if len(rows) != 12 or len({row["episode_id"] for row in rows}) != 12:
        raise RuntimeError("Expected 12 unique complete groups")
    result = {
        **qualify(rows),
        "not_executed_by_frozen_rule": [
            {"entry_index": index, "episode_id": expected[index]}
            for index in range(12, 16)
        ],
        "population_episode_ids": expected,
        "report_receipts": receipts,
        "manifest_sha256": sha(args.manifest),
        "interrupted_step": "1593640.412",
        "resume_step": "1593640.416",
        "qgf_efficacy_claim": False,
        "results": rows,
    }
    args.output.mkdir(exist_ok=False)
    report_path = args.output / "REPORT.json"
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()


if __name__ == "__main__":
    main()
