"""Combine the audited pilot and fixed remaining Support-Gradient groups."""

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
    sources = [(0, args.pilot / "REPORT.json")]
    sources.extend(
        (index, args.remaining / f"entry_{index:02d}" / "REPORT.json")
        for index in range(1, 16)
    )
    rows = []
    receipts = []
    for index, report_path in sources:
        report = json.loads(report_path.read_text())
        if report.get("episode_id") != expected[index]:
            raise RuntimeError(f"Entry {index} identity changed")
        rows.append(report)
        receipts.append({"entry_index": index, "report_sha256": sha(report_path)})
    if len(rows) != 16 or len({row["physical_input_group"] for row in rows}) != 16:
        raise RuntimeError("Expected 16 unique complete physical groups")
    result = {
        **qualify(rows),
        "population_episode_ids": expected,
        "report_receipts": receipts,
        "manifest_sha256": sha(args.manifest),
        "pilot_step": "1593640.422",
        "remaining_step": "1593640.423",
        "qgf_efficacy_claim": False,
        "results": rows,
    }
    args.output.mkdir(exist_ok=False)
    report_path = args.output / "REPORT.json"
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()


if __name__ == "__main__":
    main()
