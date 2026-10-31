#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--mock-root", required=True)
    args = parser.parse_args()
    source = Path(args.source_root).resolve()
    root = Path(args.mock_root).resolve()
    if root.exists():
        raise SystemExit("mock root already exists")
    base = root / "simplewam_visual_rl_v1"
    reg_dir = base / "formal_online_registration_v1"
    execution = base / "formal_online_execution_v1"
    reg_dir.mkdir(parents=True)
    execution.mkdir()
    registration_path = reg_dir / "REGISTRATION.json"
    registration_path.write_bytes((source / "formal_online_registration_v1" / "REGISTRATION.json").read_bytes())
    registration = json.loads(registration_path.read_text())
    registration_sha = hashlib.sha256(registration_path.read_bytes()).hexdigest()
    for task in registration["tasks"]:
        folder = execution / ("task_%03d" % task["task_index"])
        folder.mkdir()
        report = {
            "status": "SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE",
            "task_index": task["task_index"],
            "scene_index": task["scene_index"],
            "arm": task["arm"],
            "official_success": task["arm"] in ("candidate0", "uniform_random", "visual_qgf"),
            "online_registration_sha256": registration_sha,
        }
        (folder / "REPORT.json").write_text(json.dumps(report, sort_keys=True))
        (folder / "SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE").write_text("\n")
        transition = folder / "transition_0000"
        transition.mkdir()
        decision = {
            "native_supported": [True] * 4,
            "guided_supported": [True] * 4,
            "support_abstention": False,
            "selected_actions_sha256": "0" * 64,
            "outcomes_read_for_selection": 0,
        }
        (transition / "decision.json").write_text(json.dumps(decision, sort_keys=True))
    final = base / "mock_final"
    audit = base / "mock_audit"
    subprocess.run(["python3", str(source / "finalize_formal_online.py"), "--root", str(root), "--output", str(final)], check=True)
    subprocess.run(["python3", str(source / "audit_formal_online_final.py"), "--root", str(root), "--final", str(final), "--output", str(audit)], check=True)
    result = json.loads((audit / "REPORT.json").read_text())
    if result.get("status") != "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_AUDIT_PASS":
        raise SystemExit("mock audit failed")
    print(json.dumps({"status": "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_ANALYSIS_MOCK_PASS", "tasks": len(registration["tasks"]), "scenes": len(registration["scenes"]), "audit": result}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
