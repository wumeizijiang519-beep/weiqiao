#!/usr/bin/env python3
import ast
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
    source = root / "run_online_task_formal_final.py"
    registration_path = root / "formal_online_registration_v1" / "REGISTRATION.json"
    registration = json.loads(registration_path.read_text())
    deployment_path = Path(registration["deployment_registration"])
    deployment = json.loads(deployment_path.read_text())
    text = source.read_text()
    ast.parse(text)
    errors = []
    required = [
        'formal_online_registration_v1/REGISTRATION.json',
        'cohort["partitions"]["formal"]',
        'task_receipt["formal_manifest_index"]',
        'select_online_arm(',
        'native_score_bank=native_raw_t',
        'guided_score_bank=guided_raw_t',
        'commit_max_abs_error',
        'env.set_init_state(initial)',
        'np.max(np.abs(actual - initial)) > 1e-6',
    ]
    for snippet in required:
        if snippet not in text:
            errors.append("missing source contract: " + snippet)
    forbidden = [
        'partitions"]["validation',
        'online_registration_v2_support_abstention',
        'deployment_registration_v1/REGISTRATION.json',
    ]
    for snippet in forbidden:
        if snippet in text:
            errors.append("stale source contract: " + snippet)
    if registration.get("outcomes_read_during_registration") != 0:
        errors.append("registration outcome read")
    if registration.get("partition") != "formal" or len(registration.get("tasks", [])) != 412:
        errors.append("formal registration cardinality")
    if len(deployment.get("critic_checkpoints", [])) != 3:
        errors.append("final critic checkpoint count")
    for checkpoint in deployment.get("critic_checkpoints", []):
        path = Path(checkpoint["path"])
        if not path.exists() or sha256(path) != checkpoint["sha256"]:
            errors.append("checkpoint hash mismatch")
    if deployment.get("critic_aggregation") != "mean_of_three_full_data_final_conservative_twin_minima":
        errors.append("final critic aggregation")
    status = "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_SOURCE_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_SOURCE_AUDIT_FAIL"
    output_dir = root / "formal_online_source_audit_v1"
    output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "status": status,
        "errors": errors,
        "source_sha256": sha256(source),
        "registration_sha256": sha256(registration_path),
        "deployment_sha256": sha256(deployment_path),
        "robot_actions_executed": 0,
        "outcomes_read": 0,
        "mock_only": True,
        "scenes": 103,
        "tasks": 412,
    }
    report_path = output_dir / "REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (output_dir / status).write_text("\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
