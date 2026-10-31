"""Independent artifact audit that does not summarize confirmation outcomes."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--population", type=Path, required=True)
    parser.add_argument("--collection-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    collection = json.loads(args.collection_report.read_text())
    errors = []
    complete = {row["entry_index"]: row for row in collection["receipts"]}
    unavailable = {row["entry_index"]: row for row in collection["unavailable"]}
    if set(complete).intersection(unavailable) or set(complete) | set(unavailable) != set(range(32)):
        errors.append("terminal receipt coverage differs")
    development_complete = confirmation_complete = branches = 0
    for index, entry in enumerate(manifest["entries"]):
        folder = args.population / f"entry_{index:02d}"
        if index in unavailable:
            if sha(folder / "FAILED.txt") != unavailable[index]["failure_sha256"]:
                errors.append(f"{index}:failure receipt")
            continue
        report_path = folder / "REPORT.json"
        report = json.loads(report_path.read_text())
        if sha(report_path) != complete[index]["report_sha256"]:
            errors.append(f"{index}:report receipt")
            continue
        group = folder / entry["episode_id"]
        bank_path = group / "bank.npz"
        with np.load(bank_path, allow_pickle=False) as data:
            bank = np.asarray(data["candidates_native"], dtype=np.float32)
            hashes = data["hashes"].tolist()
            replay = float(data["candidate0_replay_error"])
        actual_hashes = [hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest() for value in bank]
        if bank.shape != (8, 32, 7) or hashes != actual_hashes or len(set(hashes)) != 8 or replay > 1e-6:
            errors.append(f"{index}:bank contract")
        if len(report.get("branches", [])) != 8:
            errors.append(f"{index}:branch count")
            continue
        branches += 8
        for branch in report["branches"]:
            candidate = int(branch["candidate_index"])
            branch_dir = group / f"candidate_{candidate}"
            trajectory = branch_dir / "trajectory.npz"
            video = branch_dir / "rollout.mp4"
            saved = json.loads((branch_dir / "result.json").read_text())
            if (saved != branch or sha(trajectory) != branch["trajectory_sha256"]
                    or sha(video) != branch["video_sha256"]):
                errors.append(f"{index}:{candidate}:artifact receipt")
                continue
            with np.load(trajectory, allow_pickle=False) as data:
                steps = len(data["actions"])
                commit = float(np.max(np.abs(data["actions"] - bank[candidate, :steps])))
                if (not 1 <= steps <= 32 or commit > 1e-6
                        or (steps < 32 and not (bool(data["done"][-1]) or bool(data["success"][-1])))):
                    errors.append(f"{index}:{candidate}:execution contract")
            for horizon in (16, 32):
                if not np.isfinite(float(branch[f"progress_at_{horizon}"]["value"])):
                    errors.append(f"{index}:{candidate}:progress")
        if entry["v2_split"] == "development": development_complete += 1
        else: confirmation_complete += 1
    if (development_complete != collection["development_complete"]
            or confirmation_complete != collection["confirmation_complete"]
            or development_complete + confirmation_complete != collection["complete_groups"]):
        errors.append("split denominator mismatch")
    admitted = collection["complete_groups"] >= 24 and confirmation_complete >= 12
    expected = "V2_COLLECTION_ADMIT" if admitted else "V2_COLLECTION_INSUFFICIENT"
    if collection["status"] != expected:
        errors.append("collection status mismatch")
    result = {"status": "V2_COLLECTION_AUDIT_PASS" if not errors else "V2_COLLECTION_AUDIT_FAIL",
              "errors": errors, "complete_groups": collection["complete_groups"],
              "development_complete": development_complete,
              "confirmation_complete": confirmation_complete, "branches": branches,
              "collection_status": collection["status"],
              "collection_report_sha256": sha(args.collection_report),
              "confirmation_outcomes_summarized": False,
              "online_qgf_efficacy": None}
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output.parent / result["status"]).touch()
    if errors:
        raise SystemExit(2)


if __name__ == "__main__": main()
