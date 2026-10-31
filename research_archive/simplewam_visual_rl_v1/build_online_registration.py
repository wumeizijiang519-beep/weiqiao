"""Freeze the outcome-independent 64-scene, four-arm online schedule."""

import argparse
import hashlib
import json
from pathlib import Path

from simplewam_visual_rl.online_contract import ARMS, frozen_arm_order


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scene_key(entry: dict, index: int) -> str:
    for key in ("physical_input_group", "state_sha256", "scene_key"):
        if entry.get(key):
            return str(entry[key])
    return f"validation-{index:02d}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "simplewam_visual_rl_v1"
    deployment_path = base / "deployment_registration_v1/REGISTRATION.json"
    deployment = json.loads(deployment_path.read_text())
    if deployment["status"] != "SIMPLEWAM_VISUAL_QGF_DEPLOYMENT_REGISTERED":
        raise RuntimeError("frozen deployment registration is required")
    deployment_audit = base / "deployment_audit_v1/REPORT.json"
    if json.loads(deployment_audit.read_text())["status"] != "SIMPLEWAM_VISUAL_QGF_DEPLOYMENT_AUDIT_PASS":
        raise RuntimeError("frozen deployment audit is required")
    cohort_path = Path(deployment["online_validation"]["cohort_manifest"])
    if sha256(cohort_path) != deployment["online_validation"]["cohort_manifest_sha256"]:
        raise RuntimeError("held-out cohort manifest changed")
    cohort = json.loads(cohort_path.read_text())
    validation = cohort["partitions"]["validation"]
    if len(validation) != 64:
        raise RuntimeError("expected exactly 64 held-out validation scenes")

    arm_seed = 202644501
    random_seed = 202644502
    tasks = []
    for index, entry in enumerate(validation):
        key = scene_key(entry, index)
        order = frozen_arm_order(key, arm_seed)
        for order_index, arm in enumerate(order):
            tasks.append({
                "task_index": len(tasks), "scene_index": index,
                "scene_key": key, "arm": arm, "arm_order_index": order_index,
                "arm_order": list(order), "arm_order_seed": arm_seed,
                "uniform_random_seed": random_seed,
            })
    if len(tasks) != 256 or {task["arm"] for task in tasks} != set(ARMS):
        raise RuntimeError("online schedule is incomplete")

    registration = {
        "status": "SIMPLEWAM_VISUAL_QGF_ONLINE_REGISTERED",
        "backbone": "Simple-WAM", "benchmark": "LIBERO",
        "deployment_registration": str(deployment_path),
        "deployment_registration_sha256": sha256(deployment_path),
        "deployment_audit_sha256": sha256(deployment_audit),
        "cohort_manifest": str(cohort_path), "cohort_manifest_sha256": sha256(cohort_path),
        "partition": "validation", "scenes": 64, "tasks": tasks,
        "arms": list(ARMS), "native_candidates": 4,
        "same_denoising_budget": True,
        "shadow_critic_and_gradient_for_all_arms": True,
        "outcomes_read_during_registration": 0,
        "execution": {"max_steps": 700, "replan": 10, "dummy_wait": 30,
                      "commit_max_abs_error": 1e-6},
        "primary_endpoint": "official_success",
        "admit_rule": "visual_qgf improves candidate0 and uniform_random and is noninferior to critic_rerank",
        "formal_partition_locked": True,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    path = args.output / "REGISTRATION.json"
    path.write_text(json.dumps(registration, indent=2, sort_keys=True))
    report = {
        "status": registration["status"], "registration_sha256": sha256(path),
        "scenes": 64, "tasks": 256, "arms_per_scene": 4,
        "outcomes_read": 0,
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / registration["status"]).touch()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
