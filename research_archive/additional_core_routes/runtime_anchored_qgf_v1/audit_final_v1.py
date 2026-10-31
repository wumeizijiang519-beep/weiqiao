"""Independent artifact and statistic audit for Runtime-Anchored QGF V1."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from final_metrics import qualify


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--remaining", type=Path, required=True)
    parser.add_argument("--resume", type=Path, required=True)
    parser.add_argument("--final-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    final = json.loads(args.final_report.read_text())
    errors = []
    rows = final.get("results", [])
    if len(rows) != 12 or final.get("complete_groups") != 12:
        errors.append("complete group count")
    if [item.get("entry_index") for item in final.get("not_executed_by_frozen_rule", [])] != [12, 13, 14, 15]:
        errors.append("frozen nonexecution rule")
    for row in rows:
        index = final["population_episode_ids"].index(row["episode_id"])
        if index == 0:
            folder = args.pilot
        elif index <= 10:
            folder = args.remaining / f"entry_{index:02d}"
        elif index == 11:
            folder = args.resume
        else:
            errors.append(f"unexpected result index {index}")
            continue
        group = folder / row["episode_id"]
        bank_path = group / "bank.npz"
        if len(row.get("branches", [])) != 8 or not bank_path.exists():
            errors.append(f"{index}:missing N8 artifacts")
            continue
        with np.load(bank_path, allow_pickle=False) as data:
            bank = np.asarray(data["candidates_native"], dtype=np.float32)
            hashes = data["hashes"].tolist()
            replay = float(data["candidate0_replay_error"])
        actual_hashes = [
            hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
            for value in bank
        ]
        if (
            bank.shape != (8, 32, 7)
            or hashes != actual_hashes
            or len(set(hashes)) != 8
            or replay > 1e-6
        ):
            errors.append(f"{index}:bank contract")
            continue
        for branch in row["branches"]:
            candidate = int(branch["candidate_index"])
            branch_dir = group / f"candidate_{candidate}"
            trajectory = branch_dir / "trajectory.npz"
            video = branch_dir / "rollout.mp4"
            saved = json.loads((branch_dir / "result.json").read_text())
            if (
                saved != branch
                or sha(trajectory) != branch["trajectory_sha256"]
                or sha(video) != branch["video_sha256"]
            ):
                errors.append(f"{index}:{candidate}:receipt hash")
                continue
            with np.load(trajectory, allow_pickle=False) as data:
                steps = len(data["actions"])
                commit = float(
                    np.max(np.abs(data["actions"] - bank[candidate, :steps]))
                )
                if (
                    not 1 <= steps <= 32
                    or commit > 1e-6
                    or (
                        steps < 32
                        and not (bool(data["done"][-1]) or bool(data["success"][-1]))
                    )
                ):
                    errors.append(f"{index}:{candidate}:execution contract")
            for horizon in (16, 32):
                if not np.isfinite(float(branch[f"progress_at_{horizon}"]["value"])):
                    errors.append(f"{index}:{candidate}:progress")
    recomputed = qualify(rows)
    for key in (
        "status",
        "complete_groups",
        "horizon16",
        "horizon32",
        "bootstrap_seed",
        "bootstrap_draws",
    ):
        if recomputed[key] != final.get(key):
            errors.append(f"recompute mismatch: {key}")
    result = {
        "status": (
            "RUNTIME_ANCHORED_FINAL_AUDIT_PASS"
            if not errors
            else "RUNTIME_ANCHORED_FINAL_AUDIT_FAIL"
        ),
        "errors": errors,
        "groups": len(rows),
        "branches": sum(len(row.get("branches", [])) for row in rows),
        "final_status": final.get("status"),
        "final_report_sha256": sha(args.final_report),
        "independent_qualification": recomputed,
        "qgf_efficacy_claim": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output.parent / result["status"]).touch()
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
