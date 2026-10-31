"""Independently audit the fixed first-group failure-critical pilot."""

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
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    errors = []
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("authorization_scope") != "PILOT_GROUP_0_ONLY":
        errors.append("authorization_scope")
    entry = manifest["entries"][0]
    report_path = args.run / "REPORT.json"
    if not report_path.exists():
        errors.append("missing_report")
        report = {}
    else:
        report = json.loads(report_path.read_text())
    if report.get("entry_start") != 0 or report.get("entry_stop") != 1:
        errors.append("entry_slice")
    if report.get("complete_groups") != 1 or report.get("unavailable_groups") != 0:
        errors.append("completion")
    group = args.run / entry["episode_id"]
    group_result_path = group / "RESULT.json"
    if not group_result_path.exists() or not (group / "GROUP_COMPLETE").exists():
        errors.append("group_markers")
        result = {}
    else:
        result = json.loads(group_result_path.read_text())
    bank_path = group / "bank.npz"
    if not bank_path.exists():
        errors.append("bank")
        bank = np.empty((0, 32, 7), np.float32)
    else:
        with np.load(bank_path, allow_pickle=False) as data:
            bank = np.asarray(data["candidates_native"], dtype=np.float32)
            replay_error = float(data["candidate0_replay_error"])
        if bank.shape != (8, 32, 7) or not np.isfinite(bank).all():
            errors.append("bank_shape_or_finite")
        if len({hashlib.sha256(row.tobytes()).hexdigest() for row in bank}) != 8:
            errors.append("bank_unique")
        if replay_error > 1e-6:
            errors.append("candidate0_replay")
    branches = result.get("branches", [])
    if len(branches) != 8 or sorted(row.get("candidate_index") for row in branches) != list(range(8)):
        errors.append("branch_inventory")
    for branch in branches:
        try:
            index = branch["candidate_index"]
            folder = group / f"candidate_{index}"
            trajectory = folder / "trajectory.npz"
            video = folder / "rollout.mp4"
            if sha(trajectory) != branch["trajectory_sha256"] or sha(video) != branch["video_sha256"]:
                raise RuntimeError("artifact_hash")
            with np.load(trajectory, allow_pickle=False) as data:
                actions = np.asarray(data["actions"], dtype=np.float32)
                rewards = np.asarray(data["rewards"])
                done = np.asarray(data["done"], dtype=bool)
                success = np.asarray(data["success"], dtype=bool)
                states = np.asarray(data["sim_states"])
            steps = branch["steps"]
            if not (1 <= steps <= 32 and len(actions) == len(rewards) == len(done) == len(success) == len(states) == steps):
                raise RuntimeError("trajectory_length")
            if float(np.max(np.abs(actions - bank[index, :steps]))) > 1e-6:
                raise RuntimeError("commit")
            if branch["commit_max_error"] > 1e-6:
                raise RuntimeError("reported_commit")
            if steps < 32 and not (done[-1] or success[-1]):
                raise RuntimeError("early_stop")
            if branch["success"] != bool(success[-1]) or branch["environment_done"] != bool(done[-1]):
                raise RuntimeError("terminal_receipt")
        except BaseException as exc:
            errors.append(f"candidate_{branch.get('candidate_index')}:{exc}")
    status = ("FAILURE_CRITICAL_BOUNDARY_V1_PILOT_AUDIT_PASS"
              if not errors else "FAILURE_CRITICAL_BOUNDARY_V1_PILOT_AUDIT_FAIL")
    audit = {
        "status": status,
        "errors": errors,
        "manifest_sha256": sha(args.manifest),
        "run_report_sha256": sha(report_path) if report_path.exists() else None,
        "groups": report.get("complete_groups", 0),
        "branches": len(branches),
        "remaining_groups_authorized": False,
        "qgf_efficacy_claim": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True))
    (args.output.parent / status).touch()
    print(json.dumps(audit, indent=2, sort_keys=True))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
