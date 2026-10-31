"""Independently audit Setwise-Contrastive population artifacts and gate."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


TIE_TOLERANCE = 1e-6


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--remaining", type=Path, required=True)
    parser.add_argument("--final-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    final = json.loads(args.final_report.read_text())
    index_by_episode = {entry["episode_id"]: index for index, entry in enumerate(manifest["entries"])}
    split_by_episode = {entry["episode_id"]: entry["setwise_split"] for entry in manifest["entries"]}
    errors = []
    family_non_ties = {"development": defaultdict(int), "confirmation": defaultdict(int)}
    split_counts = {"development": 0, "confirmation": 0}
    for row in final.get("results", []):
        episode = row.get("episode_id")
        if episode not in index_by_episode:
            errors.append(f"unknown episode {episode}")
            continue
        index = index_by_episode[episode]
        folder = args.pilot if index == 0 else args.remaining / f"entry_{index:02d}"
        report_path = folder / "REPORT.json"
        if not report_path.exists() or json.loads(report_path.read_text()) != row:
            errors.append(f"{index}: report receipt")
            continue
        group = folder / episode
        bank_path = group / "bank.npz"
        if len(row.get("branches", [])) != 8 or not bank_path.exists():
            errors.append(f"{index}: N8 artifacts")
            continue
        with np.load(bank_path, allow_pickle=False) as data:
            bank = np.asarray(data["candidates_native"], dtype=np.float32)
            hashes = data["hashes"].tolist()
            replay = float(data["candidate0_replay_error"])
        actual_hashes = [hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest() for value in bank]
        if bank.shape != (8, 32, 7) or hashes != actual_hashes or len(set(hashes)) != 8 or replay > 1e-6:
            errors.append(f"{index}: bank contract")
            continue
        values = []
        for branch in row["branches"]:
            candidate = int(branch["candidate_index"])
            branch_dir = group / f"candidate_{candidate}"
            trajectory = branch_dir / "trajectory.npz"
            video = branch_dir / "rollout.mp4"
            if sha(trajectory) != branch["trajectory_sha256"] or sha(video) != branch["video_sha256"]:
                errors.append(f"{index}:{candidate}: artifact hash")
                continue
            with np.load(trajectory, allow_pickle=False) as data:
                steps = len(data["actions"])
                commit = float(np.max(np.abs(data["actions"] - bank[candidate, :steps])))
                if not 1 <= steps <= 32 or commit > 1e-6 or (steps < 32 and not (bool(data["done"][-1]) or bool(data["success"][-1]))):
                    errors.append(f"{index}:{candidate}: execution contract")
            values.append(float(branch["progress_at_32"]["value"]))
        split = split_by_episode[episode]
        split_counts[split] += 1
        if len(values) == 8 and max(values) - min(values) > TIE_TOLERANCE:
            family_non_ties[split][row["family"]] += 1
    gates = {
        split: {
            "complete_groups": split_counts[split],
            "non_tie_families": sorted(family_non_ties[split]),
            "non_tie_groups_by_family": dict(sorted(family_non_ties[split].items())),
        }
        for split in split_counts
    }
    admitted = all(gates[split]["complete_groups"] >= 12 and len(gates[split]["non_tie_families"]) >= 2 for split in gates)
    expected_status = "SETWISE_CONTRASTIVE_DATA_ADMIT" if admitted else "SETWISE_CONTRASTIVE_DATA_INSUFFICIENT"
    if final.get("status") != expected_status or final.get("split_gates") != gates:
        errors.append("independent gate mismatch")
    result = {
        "status": "SETWISE_CONTRASTIVE_FINAL_AUDIT_PASS" if not errors else "SETWISE_CONTRASTIVE_FINAL_AUDIT_FAIL",
        "errors": errors,
        "final_status": final.get("status"),
        "groups": len(final.get("results", [])),
        "branches": sum(len(row.get("branches", [])) for row in final.get("results", [])),
        "independent_split_gates": gates,
        "final_report_sha256": sha(args.final_report),
        "qgf_efficacy_claim": False,
    }
    args.output.mkdir(exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
