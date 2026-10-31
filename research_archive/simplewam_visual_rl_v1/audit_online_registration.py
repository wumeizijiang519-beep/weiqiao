"""Independent fail-closed audit of the frozen online evaluation schedule."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from simplewam_visual_rl.online_contract import ARMS, frozen_arm_order


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.registration.read_text())
    errors = []
    if document.get("status") != "SIMPLEWAM_VISUAL_QGF_ONLINE_REGISTERED":
        errors.append("registration status")
    tasks = document.get("tasks", [])
    if len(tasks) != 256 or document.get("scenes") != 64:
        errors.append("schedule cardinality")
    by_scene = defaultdict(list)
    for task in tasks:
        by_scene[task.get("scene_index")].append(task)
    if set(by_scene) != set(range(64)):
        errors.append("scene indices")
    for scene_index, group in by_scene.items():
        if Counter(item.get("arm") for item in group) != Counter(ARMS):
            errors.append(f"scene {scene_index} arm coverage")
            continue
        group.sort(key=lambda item: item["arm_order_index"])
        key, seed = group[0]["scene_key"], group[0]["arm_order_seed"]
        expected = frozen_arm_order(key, seed)
        if tuple(item["arm"] for item in group) != expected:
            errors.append(f"scene {scene_index} arm order")
        if any(tuple(item["arm_order"]) != expected for item in group):
            errors.append(f"scene {scene_index} order receipt")
    forbidden = {"reward", "rewards", "success", "outcome", "return"}
    if any(key.lower() in forbidden for task in tasks for key in task):
        errors.append("outcome field in schedule")
    if document.get("outcomes_read_during_registration") != 0:
        errors.append("outcome read count")
    if document.get("arms") != list(ARMS):
        errors.append("arm declaration")
    if not document.get("shadow_critic_and_gradient_for_all_arms"):
        errors.append("shadow compute contract")
    status = "SIMPLEWAM_VISUAL_QGF_ONLINE_REGISTRATION_AUDIT_PASS" if not errors else "ONLINE_REGISTRATION_AUDIT_FAILED"
    args.output.mkdir(parents=True, exist_ok=False)
    report = {
        "status": status, "errors": errors, "registration_sha256": sha256(args.registration),
        "scenes": len(by_scene), "tasks": len(tasks), "outcome_fields": 0,
    }
    path = args.output / "REPORT.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / status).touch()
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
