"""Finalize V2 collection without exposing locked confirmation labels."""

import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--population", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest["groups"] != 32 or manifest["development_groups"] != 16 or manifest["confirmation_groups"] != 16:
        raise RuntimeError("Frozen V2 population changed")
    complete, unavailable, development, confirmation_receipts = [], [], [], []
    for index, entry in enumerate(manifest["entries"]):
        folder = args.population / f"entry_{index:02d}"
        report_path = folder / "REPORT.json"
        failed_path = folder / "FAILED.txt"
        if report_path.exists():
            report = json.loads(report_path.read_text())
            if report.get("episode_id") != entry["episode_id"] or report.get("physical_input_group") != entry["physical_input_group"]:
                raise RuntimeError(f"Entry identity changed: {index}")
            receipt = {"entry_index": index, "episode_id": entry["episode_id"],
                       "split": entry["v2_split"], "report_sha256": sha(report_path)}
            complete.append(receipt)
            if entry["v2_split"] == "development":
                development.append(report)
            else:
                confirmation_receipts.append(receipt)
        elif failed_path.exists():
            unavailable.append({"entry_index": index, "episode_id": entry["episode_id"],
                                "split": entry["v2_split"], "failure_sha256": sha(failed_path)})
        else:
            raise RuntimeError(f"Entry lacks terminal receipt: {index}")
    development_complete = sum(row["split"] == "development" for row in complete)
    confirmation_complete = sum(row["split"] == "confirmation" for row in complete)
    admitted = len(complete) >= 24 and confirmation_complete >= 12
    args.output.mkdir(parents=True, exist_ok=False)
    collection = {"status": "V2_COLLECTION_ADMIT" if admitted else "V2_COLLECTION_INSUFFICIENT",
                  "complete_groups": len(complete), "development_complete": development_complete,
                  "confirmation_complete": confirmation_complete, "unavailable": unavailable,
                  "receipts": complete, "manifest_sha256": sha(args.manifest),
                  "confirmation_labels_read_for_selection": False,
                  "online_qgf_efficacy": None}
    (args.output / "COLLECTION_REPORT.json").write_text(json.dumps(collection, indent=2, sort_keys=True))
    (args.output / "DEVELOPMENT_LABELS.json").write_text(json.dumps({
        "status": "V2_DEVELOPMENT_LABELS_RELEASED" if admitted else "V2_DEVELOPMENT_NOT_RELEASED",
        "groups": development if admitted else [], "source_manifest_sha256": sha(args.manifest)},
        indent=2, sort_keys=True))
    (args.output / "CONFIRMATION_SEAL.json").write_text(json.dumps({
        "status": "V2_CONFIRMATION_LABELS_SEALED",
        "receipts": confirmation_receipts,
        "release_condition": "development OOF gate passes and model/source hashes are frozen"},
        indent=2, sort_keys=True))
    (args.output / collection["status"]).touch()


if __name__ == "__main__": main()
