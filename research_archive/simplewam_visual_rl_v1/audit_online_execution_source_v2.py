"""Fail-closed source audit for the frozen four-lane online executor."""

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


def require(text, fragments, errors, label):
    for fragment in fragments:
        if fragment not in text:
            errors.append(f"{label} missing {fragment!r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "simplewam_visual_rl_v1"
    registration = base / "online_registration_v2_support_abstention/REGISTRATION.json"
    reg = json.loads(registration.read_text())
    runner = (base / "run_online_task_v2.py").read_text()
    lane = (base / "run_online_lane_v2.sh").read_text()
    watcher = (base / "run_online_v2.sh").read_text()
    scheduler = (base / "simplewam_visual_rl/scheduler.py").read_text()
    errors = []
    if reg.get("status") != "SIMPLEWAM_VISUAL_QGF_ONLINE_REGISTERED" or len(reg.get("tasks", [])) != 240:
        errors.append("online registration")
    require(runner, (
        "select_online_arm(", "native_bank=np.stack(native)", "guided_bank=np.stack(guided)",
        "native_score_bank=native_raw_t", "guided_score_bank=guided_raw_t",
        "features=features", "token=state", '"decision.json"', '"feedback.npz"', '"official_success"',
        "commit_max_abs_error", "save_rng(", "rollout.mp4",
    ), errors, "runner")
    require(scheduler, (
        'self.arm == "visual_qgf"', "self.frozen_q.guide_velocity(",
        '"shadow_computed": True', '"guidance_committed"',
    ), errors, "scheduler")
    require(lane, (
        'seq "$LANE" 4 239', "SIMPLEWAM_VISUAL_QGF_WAM_COMPATIBILITY_PASS",
        "LANE_${LANE}_LAST_COMPLETE_TASK", "SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE",
    ), errors, "lane")
    require(watcher, (
        "--exclusive -N1 -n1 --gres=gpu:1", "SIMPLEWAM_VISUAL_QGF_WAM_COMPATIBILITY_PASS", "for LANE in 0 1 2 3",
        "run_online_lane_v2.sh",
    ), errors, "watcher")
    if runner.find("select_online_arm(") > runner.find("env.step(committed)"):
        errors.append("selection does not precede committed environment action")
    lanes = [list(range(index, 240, 4)) for index in range(4)]
    flat = [item for values in lanes for item in values]
    if sorted(flat) != list(range(240)) or len(flat) != len(set(flat)):
        errors.append("four-lane partition")
    status = "SIMPLEWAM_VISUAL_QGF_ONLINE_EXECUTION_SOURCE_AUDIT_PASS" if not errors else "ONLINE_EXECUTION_SOURCE_AUDIT_FAILED"
    args.output.mkdir(parents=True, exist_ok=False)
    report = {
        "status": status, "errors": errors, "tasks": 240, "lanes": 4,
        "registration_sha256": sha256(registration),
        "source_sha256": {
            name: sha256(base / name) for name in (
                "run_online_task_v2.py", "run_online_lane_v2.sh", "run_online_v2.sh",
                "run_wam_compatibility_gate.py", "run_wam_compatibility_gate.sh",
                "simplewam_visual_rl/scheduler.py", "simplewam_visual_rl/online_contract.py",
            )
        },
        "robot_actions_executed": 0,
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / status).touch()
    print(json.dumps(report, indent=2))
    if errors: raise SystemExit(1)


if __name__ == "__main__":
    main()
