"""Independent fail-closed audit of the runtime-anchored pilot artifacts."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    report = json.loads((args.run / "REPORT.json").read_text())
    errors = []
    if report.get("status") != "ENSEMBLE_DISAGREEMENT_GROUP_COMPLETE":
        errors.append("runner status is not complete")
    if report.get("boundary_contract") != "RUNTIME_ANCHORED_SINGLE_SOURCE_POLICY_INPUT_V1":
        errors.append("runtime-anchored boundary contract missing")
    if len(report.get("branches", [])) != 8 or sorted(report.get("branch_order", [])) != list(range(8)):
        errors.append("branch population is not exact N8")
    group = args.run / report.get("episode_id", "missing")
    bank_path = group / "bank.npz"
    if not bank_path.exists():
        errors.append("bank artifact missing")
    else:
        with np.load(bank_path, allow_pickle=False) as bank:
            native = bank["candidates_native"]
            hashes = bank["hashes"].tolist()
            if native.shape != (8, 32, 7) or not np.isfinite(native).all():
                errors.append("invalid native bank")
            actual_hashes = [hashlib.sha256(np.ascontiguousarray(row).tobytes()).hexdigest()
                             for row in native]
            if hashes != actual_hashes or len(set(hashes)) != 8:
                errors.append("candidate hash audit failed")
            if float(bank["candidate0_replay_error"]) > 1e-6:
                errors.append("candidate0 replay exceeds tolerance")
            if not np.array_equal(native[4:, :, 6], np.broadcast_to(native[0, :, 6], (4, 32))):
                errors.append("disagreement projection changed gripper")
            norms = np.asarray(bank["structured_delta_norms"])
            if norms.shape != (4,) or not np.all(np.diff(norms) > 0):
                errors.append("disagreement radius schedule invalid")
            for row in report.get("branches", []):
                index = int(row["candidate_index"])
                branch = group / f"candidate_{index}"
                trajectory = branch / "trajectory.npz"
                video = branch / "rollout.mp4"
                if sha(trajectory) != row["trajectory_sha256"] or sha(video) != row["video_sha256"]:
                    errors.append(f"artifact hash mismatch for candidate {index}")
                    continue
                with np.load(trajectory, allow_pickle=False) as data:
                    steps = len(data["actions"])
                    expected = native[index, :steps]
                    error = float(np.max(np.abs(data["actions"] - expected)))
                    if steps < 1 or steps > 32 or error > 1e-6 or error != row["commit_max_error"]:
                        errors.append(f"execution contract failed for candidate {index}")
                    early = steps < 32
                    if early and not (bool(data["done"][-1]) or bool(data["success"][-1])):
                        errors.append(f"invalid early stop for candidate {index}")
                for horizon in (16, 32):
                    progress = row[f"progress_at_{horizon}"]
                    if not np.isfinite(progress["value"]):
                        errors.append(f"non-finite progress for candidate {index}")
                if not isinstance(row.get("branch_boundary_observation_hash"), str):
                    errors.append(f"branch observation receipt missing for candidate {index}")
    result = {
        "status": "ENSEMBLE_DISAGREEMENT_PILOT_AUDIT_PASS" if not errors else "ENSEMBLE_DISAGREEMENT_PILOT_AUDIT_FAIL",
        "errors": errors,
        "runner_report_sha256": sha(args.run / "REPORT.json"),
        "bank_sha256": sha(bank_path) if bank_path.exists() else None,
        "qgf_efficacy_claim": False,
    }
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(2)
    (args.output / "ENSEMBLE_DISAGREEMENT_PILOT_AUDIT_PASS").touch()


if __name__ == "__main__":
    main()
