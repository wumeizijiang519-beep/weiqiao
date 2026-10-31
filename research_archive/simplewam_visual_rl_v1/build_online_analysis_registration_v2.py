"""Freeze online-analysis statistics before any held-out result exists."""

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
    online = base / "online_registration_v2_support_abstention/REGISTRATION.json"
    source_audit = base / "online_execution_source_audit_v2_support_abstention/REPORT.json"
    if json.loads(online.read_text()).get("status") != "SIMPLEWAM_VISUAL_QGF_ONLINE_REGISTERED":
        raise RuntimeError("frozen online registration required")
    if json.loads(source_audit.read_text()).get("status") != "SIMPLEWAM_VISUAL_QGF_ONLINE_EXECUTION_SOURCE_AUDIT_PASS":
        raise RuntimeError("online executor source audit required")
    document = {
        "status": "SIMPLEWAM_VISUAL_QGF_ONLINE_ANALYSIS_REGISTERED",
        "online_registration_sha256": sha256(online),
        "execution_source_audit_sha256": sha256(source_audit),
        "required_scenes": 60,
        "scene_indices": list(range(4, 64)),
        "required_arms": ["candidate0", "uniform_random", "critic_rerank", "visual_qgf"],
        "primary_endpoint": "official_success",
        "unit": "physical_scene_equal_weight",
        "paired_bootstrap": {"seed": 202644601, "draws": 10000, "interval": [0.025, 0.975]},
        "noninferiority_margin_vs_critic_rerank": 0.05,
        "admit_rule": {
            "visual_qgf_minus_candidate0_lower95_gt": 0.0,
            "visual_qgf_minus_uniform_random_lower95_gt": 0.0,
            "visual_qgf_minus_critic_rerank_lower95_gte": -0.05,
        },
        "missing_task_policy": "fail_closed_no_scientific_conclusion",
        "support_abstention_is_safety_metric_not_endpoint": True,
        "outcomes_read_during_registration": 0,
        "secondary_metrics": ["paired_discordance", "wall_seconds", "decision_latency", "video_frames", "gpu_cost"],
    }
    args.output.mkdir(parents=True, exist_ok=False)
    path = args.output / "REGISTRATION.json"
    path.write_text(json.dumps(document, indent=2, sort_keys=True))
    report = {"status": document["status"], "registration_sha256": sha256(path), "outcomes_read": 0}
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / document["status"]).touch()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
