"""Independent fail-closed audit of the non-authorized execution manifest."""

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
    import torch

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    errors = []
    if manifest.get("status") != "FAILURE_CRITICAL_BOUNDARY_V1_EXECUTION_READY_AWAITING_AUTHORIZATION":
        errors.append("status")
    if manifest.get("gpu_execution_authorized") is not False:
        errors.append("authorization")
    entries = manifest.get("entries", [])
    if len(entries) != 16:
        errors.append("entry_count")
    if len({row.get("physical_input_group") for row in entries}) != 16:
        errors.append("physical_groups")
    family_counts = {}
    for row in entries:
        family_counts[row.get("family")] = family_counts.get(row.get("family"), 0) + 1
        try:
            summary_path = Path(row["episode_directory"]) / "summary.json"
            if sha(summary_path) != row["summary_sha256"]:
                raise RuntimeError("summary")
            summary = json.loads(summary_path.read_text())
            for key in ("task_name", "state_sha256", "task_id", "environment_seed",
                        "initial_state_index", "initial_state_path", "initial_file_sha256"):
                if row[key] != summary[key]:
                    raise RuntimeError(key)
            states = np.asarray(torch.load(row["initial_state_path"], map_location="cpu",
                                           weights_only=False))
            if "_add_" in Path(row["initial_state_path"]).name or "_level" in Path(row["initial_state_path"]).name:
                states = states.reshape(1, -1)
            state = np.asarray(states[row["initial_state_index"]], dtype="<f8")
            if hashlib.sha256(state.tobytes()).hexdigest() != row["state_sha256"]:
                raise RuntimeError("state")
            actions, rewards, dones, successes = [], [], [], []
            receipts = row["transition_receipts"]
            if len(receipts) != row["boundary_replan"]:
                raise RuntimeError("receipt_count")
            for index, receipt in enumerate(receipts):
                transition = Path(row["episode_directory"]) / f"transition_{index:04d}/transition.npz"
                if receipt["index"] != index or sha(transition) != receipt["sha256"]:
                    raise RuntimeError("transition_receipt")
                with np.load(transition, allow_pickle=False) as data:
                    actual = int(data["actual_length"])
                    if actual != receipt["actual_length"]:
                        raise RuntimeError("transition_length")
                    actions.append(np.asarray(data["executed_actions"][:actual], dtype=np.float32))
                    rewards.append(np.asarray(data["rewards"][:actual], dtype=np.float64))
                    dones.append(np.asarray(data["step_environment_done"][:actual], dtype=bool))
                    successes.append(np.asarray(data["step_success"][:actual], dtype=bool))
            values = {
                "prefix_actions_sha256": np.concatenate(actions) if actions else np.empty((0, 7), np.float32),
                "prefix_rewards_sha256": np.concatenate(rewards) if rewards else np.empty(0, np.float64),
                "prefix_done_sha256": np.concatenate(dones) if dones else np.empty(0, bool),
                "prefix_success_sha256": np.concatenate(successes) if successes else np.empty(0, bool),
            }
            if len(values["prefix_actions_sha256"]) != row["prefix_steps"]:
                raise RuntimeError("prefix_steps")
            for key, value in values.items():
                if hashlib.sha256(value.tobytes()).hexdigest() != row[key]:
                    raise RuntimeError(key)
            if sha(row["boundary_observation_path"]) != row["boundary_observation_sha256"]:
                raise RuntimeError("boundary_observation")
        except BaseException as exc:
            errors.append(f"{row.get('episode_id')}:{exc}")
    if sorted(family_counts.values()) != [4, 4, 4, 4]:
        errors.append("family_balance")
    report = {
        "status": ("FAILURE_CRITICAL_BOUNDARY_V1_EXECUTION_READY_AUDIT_PASS"
                   if not errors else "FAILURE_CRITICAL_BOUNDARY_V1_EXECUTION_READY_AUDIT_FAIL"),
        "gpu_execution_authorized": False,
        "manifest_sha256": sha(args.manifest),
        "groups": len(entries),
        "family_counts": family_counts,
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output.parent / report["status"]).touch()
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
