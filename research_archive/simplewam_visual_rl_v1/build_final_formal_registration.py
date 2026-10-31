#!/usr/bin/env python3
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ARMS = ("candidate0", "uniform_random", "critic_rerank", "visual_qgf")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rank(seed, *parts):
    payload = "|".join([str(seed)] + [str(part) for part in parts]).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def frozen_order(scene_key, seed):
    return tuple(sorted(ARMS, key=lambda arm: rank(seed, scene_key, arm)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    ensemble_path = root / "final_critic_ensemble_v1" / "REGISTRATION.json"
    ensemble = json.loads(ensemble_path.read_text())
    if ensemble.get("status") != "SIMPLEWAM_VISUAL_IQL_FINAL_ENSEMBLE_FROZEN":
        raise SystemExit("final ensemble is not frozen")
    old_deployment_path = root / "deployment_registration_v1" / "REGISTRATION.json"
    old = json.loads(old_deployment_path.read_text())
    cohort_path = Path(old["online_validation"]["cohort_manifest"])
    cohort = json.loads(cohort_path.read_text())
    if sha256(cohort_path) != old["online_validation"]["cohort_manifest_sha256"]:
        raise SystemExit("cohort manifest changed")
    formal = cohort["partitions"]["formal"]
    grouped = defaultdict(list)
    for entry_index, entry in enumerate(formal):
        grouped[entry["physical_input_group"]].append((entry_index, entry))
    selection_seed = 202644701
    selected = []
    for group, options in grouped.items():
        entry_index, entry = min(options, key=lambda pair: rank(selection_seed, group, pair[1]["episode_id"], pair[1]["task_name"]))
        selected.append((group, entry_index, entry))
    selected.sort(key=lambda row: rank(selection_seed, row[0]))
    if len(selected) != 103:
        raise SystemExit("expected 103 unique formal physical groups")
    deployment_dir = root / "final_critic_deployment_v1"
    formal_dir = root / "formal_online_registration_v1"
    if deployment_dir.exists() or formal_dir.exists():
        raise SystemExit("output already exists")
    deployment_dir.mkdir()
    deployment = dict(old)
    deployment["critic_aggregation"] = "mean_of_three_full_data_final_conservative_twin_minima"
    deployment["critic_checkpoints"] = ensemble["checkpoints"]
    deployment["selection_used_outcomes"] = False
    deployment["final_critic_ensemble_registration"] = str(ensemble_path)
    deployment["final_critic_ensemble_registration_sha256"] = sha256(ensemble_path)
    deployment["online_validation"] = dict(old["online_validation"])
    deployment["online_validation"].update({"partition": "formal", "scenes": 103, "formal_partition_locked": True})
    deployment_path = deployment_dir / "REGISTRATION.json"
    deployment_path.write_text(json.dumps(deployment, indent=2, sort_keys=True) + "\n")

    arm_seed = 202644702
    random_seed = 202644703
    scenes = []
    tasks = []
    for scene_index, (group, manifest_index, entry) in enumerate(selected):
        scene = {
            "scene_index": scene_index,
            "formal_manifest_index": manifest_index,
            "episode_id": entry["episode_id"],
            "physical_input_group": group,
            "state_sha256": entry["state_sha256"],
            "family": entry["family"],
            "category": entry["category"],
            "selection_seed": selection_seed,
        }
        scenes.append(scene)
        order = frozen_order(group, arm_seed)
        for order_index, arm in enumerate(order):
            tasks.append({
                "task_index": len(tasks),
                "scene_index": scene_index,
                "formal_manifest_index": manifest_index,
                "scene_key": group,
                "arm": arm,
                "arm_order_index": order_index,
                "arm_order": list(order),
                "arm_order_seed": arm_seed,
                "uniform_random_seed": random_seed,
            })
    formal_dir.mkdir()
    registration = {
        "status": "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_REGISTERED",
        "backbone": "Simple-WAM",
        "benchmark": "LIBERO-plus",
        "partition": "formal",
        "formal_entries_available": len(formal),
        "unique_physical_groups": 103,
        "scene_selection_rule": "one SHA256-ranked entry per physical_input_group",
        "scene_selection_seed": selection_seed,
        "scenes": scenes,
        "tasks": tasks,
        "arms": list(ARMS),
        "cohort_manifest": str(cohort_path),
        "cohort_manifest_sha256": sha256(cohort_path),
        "deployment_registration": str(deployment_path),
        "deployment_registration_sha256": sha256(deployment_path),
        "final_critic_ensemble_registration_sha256": sha256(ensemble_path),
        "outcomes_read_during_registration": 0,
        "previous_validation_outcomes_used": False,
        "same_native_candidates": 4,
        "same_denoising_budget": True,
        "shadow_critic_and_gradient_for_all_arms": True,
        "support_policy": {
            "candidate0_and_uniform_random_do_not_require_critic_support": True,
            "critic_rerank_uses_supported_native_candidates_only": True,
            "visual_qgf_uses_supported_guided_candidates_only": True,
            "no_supported_q_candidate_fallback": "candidate0",
            "support_bounds_unchanged": True,
        },
        "execution": {"max_steps": 700, "replan": 10, "dummy_wait": 30, "commit_max_abs_error": 1e-6},
        "primary_endpoint": "official_success",
        "analysis": {
            "paired_bootstrap_seed": 202644704,
            "paired_bootstrap_draws": 10000,
            "group_unit": "physical_input_group",
            "admit_rule": "visual_qgf minus candidate0 and uniform_random lower95 > 0 and visual_qgf minus critic_rerank lower95 >= -0.05",
            "all_103_scenes_required": True,
        },
    }
    registration_path = formal_dir / "REGISTRATION.json"
    registration_path.write_text(json.dumps(registration, indent=2, sort_keys=True) + "\n")
    report = {
        "status": registration["status"],
        "formal_scenes": 103,
        "tasks": 412,
        "families": sorted(set(scene["family"] for scene in scenes)),
        "outcomes_read": 0,
        "registration_sha256": sha256(registration_path),
        "deployment_registration_sha256": sha256(deployment_path),
    }
    (formal_dir / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (formal_dir / registration["status"]).write_text("\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
