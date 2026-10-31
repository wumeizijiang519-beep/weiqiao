#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ARMS = ("candidate0", "uniform_random", "critic_rerank", "visual_qgf")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rank(seed, *parts):
    return hashlib.sha256("|".join([str(seed)] + [str(part) for part in parts]).encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    registration_path = root / "formal_online_registration_v1" / "REGISTRATION.json"
    registration = json.loads(registration_path.read_text())
    cohort_path = Path(registration["cohort_manifest"])
    cohort = json.loads(cohort_path.read_text())
    deployment_path = Path(registration["deployment_registration"])
    deployment = json.loads(deployment_path.read_text())
    errors = []
    if sha256(cohort_path) != registration.get("cohort_manifest_sha256"):
        errors.append("cohort hash mismatch")
    if sha256(deployment_path) != registration.get("deployment_registration_sha256"):
        errors.append("deployment hash mismatch")
    formal = cohort["partitions"]["formal"]
    train_groups = {row["physical_input_group"] for row in cohort["partitions"]["train"]}
    validation_groups = {row["physical_input_group"] for row in cohort["partitions"]["validation"]}
    formal_groups = {row["physical_input_group"] for row in formal}
    if formal_groups & train_groups or formal_groups & validation_groups:
        errors.append("formal physical groups overlap prior partitions")
    scenes = registration.get("scenes", [])
    if len(scenes) != 103 or len({row["physical_input_group"] for row in scenes}) != 103:
        errors.append("formal scene cardinality")
    for scene in scenes:
        index = scene["formal_manifest_index"]
        entry = formal[index]
        if entry["physical_input_group"] != scene["physical_input_group"] or entry["state_sha256"] != scene["state_sha256"]:
            errors.append("scene source mismatch %d" % scene["scene_index"])
        for key, digest_key in (("bddl_path", "bddl_sha256"), ("initial_state_path", "initial_file_sha256")):
            path = Path(entry[key])
            if not path.exists() or sha256(path) != entry[digest_key]:
                errors.append("scene asset mismatch %d %s" % (scene["scene_index"], key))
    tasks = registration.get("tasks", [])
    by_scene = defaultdict(list)
    for task in tasks:
        by_scene[task.get("scene_index")].append(task)
    if len(tasks) != 412 or set(by_scene) != set(range(103)):
        errors.append("task cardinality")
    for scene_index, rows in by_scene.items():
        if Counter(row["arm"] for row in rows) != Counter(ARMS):
            errors.append("arm coverage %d" % scene_index)
        rows.sort(key=lambda row: row["arm_order_index"])
        expected = tuple(sorted(ARMS, key=lambda arm: rank(rows[0]["arm_order_seed"], rows[0]["scene_key"], arm)))
        if tuple(row["arm"] for row in rows) != expected:
            errors.append("arm order %d" % scene_index)
    checkpoints = deployment.get("critic_checkpoints", [])
    if [row.get("seed") for row in checkpoints] != [202644201, 202644202, 202644203]:
        errors.append("final critic seed ensemble")
    for row in checkpoints:
        path = Path(row["path"])
        if not path.exists() or sha256(path) != row["sha256"]:
            errors.append("final checkpoint hash %s" % row.get("seed"))
    if deployment.get("critic_aggregation") != "mean_of_three_full_data_final_conservative_twin_minima":
        errors.append("ensemble rule")
    if registration.get("outcomes_read_during_registration") != 0 or registration.get("previous_validation_outcomes_used") is not False:
        errors.append("outcome independence")
    qgf = deployment.get("qgf", {})
    if not (qgf.get("weight") == 0.1 and qgf.get("max_grad_norm") == 1.0 and qgf.get("gripper_gradient_masked") is True):
        errors.append("QGF deployment bytes")
    status = "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_REGISTRATION_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_REGISTRATION_AUDIT_FAIL"
    output_dir = root / "formal_online_registration_audit_v1"
    output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "status": status,
        "errors": errors,
        "registration_sha256": sha256(registration_path),
        "formal_entries": len(formal),
        "formal_unique_physical_groups": len(formal_groups),
        "train_formal_group_overlap": len(formal_groups & train_groups),
        "validation_formal_group_overlap": len(formal_groups & validation_groups),
        "scenes": len(scenes),
        "tasks": len(tasks),
        "outcomes_read": 0,
    }
    report_path = output_dir / "REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (output_dir / status).write_text("\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
