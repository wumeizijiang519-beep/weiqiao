#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    audit_path = root / "final_critic_audit_v1" / "REPORT.json"
    audit = json.loads(audit_path.read_text())
    if audit.get("status") != "SIMPLEWAM_VISUAL_IQL_FINAL_AUDIT_PASS":
        raise SystemExit("final critic audit has not passed")
    output_dir = root / "final_critic_ensemble_v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoints = []
    for worker in audit["workers"]:
        seed = int(worker["seed"])
        path = root / "final_critic_execution_v1" / ("seed_%d" % seed) / "FINAL_CRITIC.pt"
        actual_sha = sha256(path)
        if actual_sha != worker["checkpoint_sha256"]:
            raise SystemExit("checkpoint changed for seed %d" % seed)
        checkpoints.append({"seed": seed, "path": str(path), "sha256": actual_sha})
    registration = {
        "status": "SIMPLEWAM_VISUAL_IQL_FINAL_ENSEMBLE_FROZEN",
        "branch": "full_data_final_critic_retrain_v1",
        "checkpoint_rule": "fixed_final_step_50000_for_every_registered_seed",
        "per_seed_q_rule": "min_q1_q2",
        "ensemble_rule": "arithmetic_mean_across_all_three_registered_seeds",
        "seeds": [202644201, 202644202, 202644203],
        "checkpoints": checkpoints,
        "corpus_sha256": "a2337827258238d6369a0161179491ffe3629b04f113cea9c0ab3d84a56e62b0",
        "token_checkpoint_sha256": "40a436a09e618965642f680bda5d1339f3426ccd735b73aba6629fbbc46a8c97",
        "training_rows_per_seed": 12218,
        "updates_per_seed": 50000,
        "validation_or_online_outcomes_read_for_selection": 0,
        "outcome_dependent_seed_or_checkpoint_selection": False,
        "final_critic_audit_sha256": sha256(audit_path),
        "frozen_deployment_invariants": {
            "simplewam_frozen": True,
            "visual_features_frozen": True,
            "rl_token_frozen": True,
            "action_prefix_shape": [10, 7],
            "qgf_weight": 0.1,
            "qgf_max_grad_norm": 1.0,
            "gripper_gradient_masked": True,
            "support_bounds_unchanged": True,
        },
    }
    output_path = output_dir / "REGISTRATION.json"
    output_path.write_text(json.dumps(registration, indent=2, sort_keys=True) + "\n")
    digest = sha256(output_path)
    (output_dir / "REGISTRATION.sha256").write_text(digest + "  REGISTRATION.json\n")
    print("SIMPLEWAM_VISUAL_IQL_FINAL_ENSEMBLE_FROZEN")
    print("REGISTRATION_SHA256=" + digest)


if __name__ == "__main__":
    main()
