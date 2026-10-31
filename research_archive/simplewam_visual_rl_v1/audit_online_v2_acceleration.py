"""Zero-action audit for the eight-lane V2 orchestration amendment."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "simplewam_visual_rl_v1"
    registration = base / "online_registration_v2_support_abstention/REGISTRATION.json"
    document = json.loads(registration.read_text())
    worker = (base / "run_online_lane_v2_worker8.sh").read_text()
    dual = (base / "run_online_v2_dual_gpu.sh").read_text()
    dispatch = (base / "run_online_v2_accelerated.sh").read_text()
    errors = []
    if len(document.get("tasks", [])) != 240:
        errors.append("registration cardinality")
    lanes = [list(range(index, 240, 8)) for index in range(8)]
    flat = [task for lane in lanes for task in lane]
    if sorted(flat) != list(range(240)) or len(flat) != len(set(flat)):
        errors.append("logical lane partition")
    required = {
        "worker": ('seq "$LANE" 8 239', "OMP_NUM_THREADS=2", "SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE"),
        "dual": ("PHYSICAL_LANE + 4", "wait \"$P0\"", "wait \"$P1\""),
        "dispatch": ("--exclusive -N1 -n1 --gres=gpu:1", "--cpus-per-task=4", "--mem=60G"),
    }
    for label, fragments in required.items():
        text = {"worker": worker, "dual": dual, "dispatch": dispatch}[label]
        for fragment in fragments:
            if fragment not in text:
                errors.append(f"{label} missing {fragment}")
    status = "SIMPLEWAM_VISUAL_QGF_ONLINE_V2_ACCELERATION_AUDIT_PASS" if not errors else "ONLINE_V2_ACCELERATION_AUDIT_FAILED"
    report = {
        "status": status, "errors": errors, "physical_gpus": 4,
        "logical_lanes": 8, "tasks": 240, "robot_actions_executed": 0,
        "registration_sha256": sha256(registration),
        "source_sha256": {
            name: sha256(base / name) for name in (
                "ONLINE_V2_ACCELERATION_AMENDMENT.md",
                "run_online_lane_v2_worker8.sh",
                "run_online_v2_dual_gpu.sh",
                "run_online_v2_accelerated.sh",
            )
        },
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / status).touch()
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
