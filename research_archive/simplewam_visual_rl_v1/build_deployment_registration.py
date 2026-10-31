"""Freeze the outcome-independent visual-Q deployment and online-evaluation contract."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "simplewam_visual_rl_v1"
    qualification = base / "iql_qualification_v1/REPORT.json"
    audit = base / "iql_qualification_audit_v1/REPORT.json"
    if json.loads(qualification.read_text())["status"] != "SIMPLEWAM_VISUAL_IQL_QUALIFIED":
        raise RuntimeError("qualified critic required")
    if json.loads(audit.read_text())["status"] != "SIMPLEWAM_VISUAL_IQL_QUALIFICATION_AUDIT_PASS":
        raise RuntimeError("independent qualification audit required")
    checkpoints = []
    for seed in (202644201, 202644202, 202644203):
        for fold in (0, 1, 2):
            path = base / f"iql_execution_v1/seed_{seed}_fold_{fold}/proposed.pt"
            checkpoints.append({"seed": seed, "fold": fold, "path": str(path), "sha256": sha256(path)})
    corpus_path = base / "critic_corpus_v1/CORPUS.npz"
    with np.load(corpus_path, allow_pickle=False) as archive:
        actions = archive["action_prefix"]
        support_min = actions.min(axis=(0, 1)).astype(float).tolist()
        support_max = actions.max(axis=(0, 1)).astype(float).tolist()
    cohort = args.root / "qgf_gradient_v1/evidence/COHORT_MANIFEST.json"
    cohort_document = json.loads(cohort.read_text())
    if len(cohort_document["partitions"]["validation"]) != 64:
        raise RuntimeError("frozen held-out validation cohort changed")
    registration = {
        "status": "SIMPLEWAM_VISUAL_QGF_DEPLOYMENT_REGISTERED",
        "backbone": "Simple-WAM",
        "benchmark": "LIBERO",
        "token_checkpoint": str(base / "token_training_v1/TOKEN.pt"),
        "token_checkpoint_sha256": sha256(base / "token_training_v1/TOKEN.pt"),
        "critic_aggregation": "mean_of_nine_conservative_twin_minima",
        "critic_checkpoints": checkpoints,
        "selection_used_outcomes": False,
        "support_min": support_min,
        "support_max": support_max,
        "qgf": {
            "execution_horizon": 10, "action_dim": 7, "continuous_dims": 6,
            "weight": 0.1, "max_grad_norm": 1.0, "sigma_min": 0.0, "sigma_max": 1.0,
            "gripper_gradient_masked": True, "wam_gradients": False, "token_gradients": False,
        },
        "online_validation": {
            "cohort_manifest": str(cohort), "cohort_manifest_sha256": sha256(cohort),
            "partition": "validation", "scenes": 64,
            "arms": ["candidate0", "uniform_random", "critic_rerank", "visual_qgf"],
            "native_candidates": 4, "same_denoising_budget": True,
            "shadow_critic_and_gradient_for_all_arms": True,
            "primary_endpoint": "official_success",
            "admit_rule": "visual_qgf improves candidate0 and uniform_random and is noninferior to critic_rerank",
            "formal_partition_locked": True,
        },
        "qualification_report_sha256": sha256(qualification),
        "qualification_audit_sha256": sha256(audit),
        "corpus_sha256": sha256(corpus_path),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    path = args.output / "REGISTRATION.json"
    path.write_text(json.dumps(registration, indent=2))
    report = {
        "status": registration["status"], "registration_sha256": sha256(path),
        "critics": len(checkpoints), "validation_scenes": 64,
        "outcomes_read_for_model_selection": 0,
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2))
    (args.output / registration["status"]).touch()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
