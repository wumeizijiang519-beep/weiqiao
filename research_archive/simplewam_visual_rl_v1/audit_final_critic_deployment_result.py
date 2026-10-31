#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
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
    registration_path = root / "final_critic_deployment_v1" / "REGISTRATION.json"
    report_path = root / "final_critic_deployment_audit_v1" / "REPORT.json"
    registration = json.loads(registration_path.read_text())
    report = json.loads(report_path.read_text())
    errors = []
    if report.get("status") != "SIMPLEWAM_VISUAL_QGF_DEPLOYMENT_AUDIT_PASS":
        errors.append("deployment audit status")
    if report.get("registration_sha256") != sha256(registration_path):
        errors.append("registration hash link")
    if registration.get("critic_aggregation") != "mean_of_three_full_data_final_conservative_twin_minima":
        errors.append("critic aggregation")
    checkpoints = registration.get("critic_checkpoints", [])
    if [row.get("seed") for row in checkpoints] != [202644201, 202644202, 202644203]:
        errors.append("fixed seed set")
    for row in checkpoints:
        path = Path(row["path"])
        if not path.exists() or sha256(path) != row["sha256"]:
            errors.append("checkpoint hash %s" % row.get("seed"))
    scores = report.get("rerank_scores", [])
    if len(scores) != 4 or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in scores):
        errors.append("finite N4 rerank scores")
    if len(set(scores)) <= 1:
        errors.append("nontrivial rerank")
    guidance = report.get("guidance", {})
    if guidance.get("applied") is not True:
        errors.append("guidance inactive")
    norms = guidance.get("raw_grad_norm", [])
    if len(norms) != 1 or not math.isfinite(norms[0]) or norms[0] <= 0:
        errors.append("nonzero finite Q gradient")
    if guidance.get("suffix_max_error") != 0.0 or guidance.get("gripper_max_error") != 0.0:
        errors.append("gradient masking")
    if report.get("robot_actions_executed") != 0 or report.get("wam_parameters_loaded") != 0:
        errors.append("zero-action critic-only contract")
    if registration.get("selection_used_outcomes") is not False:
        errors.append("outcome-independent deployment")
    status = "SIMPLEWAM_VISUAL_QGF_FINAL_CRITIC_DEPLOYMENT_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_QGF_FINAL_CRITIC_DEPLOYMENT_AUDIT_FAIL"
    output_dir = root / "final_critic_deployment_independent_audit_v1"
    output_dir.mkdir(parents=True, exist_ok=False)
    output = {
        "status": status,
        "errors": errors,
        "registration_sha256": sha256(registration_path),
        "deployment_audit_report_sha256": sha256(report_path),
        "checkpoint_count": len(checkpoints),
        "rerank_scores": scores,
        "rerank_index": report.get("rerank_index"),
        "raw_grad_norm": norms,
        "robot_actions_executed": 0,
        "formal_outcomes_read": 0,
    }
    output_path = output_dir / "REPORT.json"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    (output_dir / status).write_text("\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
