"""Finalize the frozen four-arm online comparison after all tasks terminate."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def interval(values, seed, draws):
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    samples = values[rng.integers(0, len(values), size=(draws, len(values)))].mean(1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "simplewam_visual_rl_v1"
    analysis_path = base / "online_analysis_registration_v1_retry2/REGISTRATION.json"
    analysis = json.loads(analysis_path.read_text())
    online = json.loads((base / "online_registration_v1/REGISTRATION.json").read_text())
    execution = base / "online_execution_v1"
    arms = analysis["required_arms"]
    by_scene = {index: {} for index in range(analysis["required_scenes"])}
    receipts = []
    errors = []
    for task in online["tasks"]:
        folder = execution / f"task_{task['task_index']:03d}"
        report_path = folder / "REPORT.json"
        if not report_path.exists():
            errors.append(f"missing task {task['task_index']}")
            continue
        report = json.loads(report_path.read_text())
        if report.get("status") != "SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE":
            errors.append(f"invalid task {task['task_index']}")
            continue
        if report.get("scene_index") != task["scene_index"] or report.get("arm") != task["arm"]:
            errors.append(f"task receipt mismatch {task['task_index']}")
            continue
        by_scene[task["scene_index"]][task["arm"]] = bool(report["official_success"])
        receipts.append({"task_index": task["task_index"], "report_sha256": sha256(report_path)})
    complete = [index for index, values in by_scene.items() if set(values) == set(arms)]
    if len(complete) != analysis["required_scenes"] or errors:
        status = "SIMPLEWAM_VISUAL_QGF_ONLINE_INCOMPLETE"
        result = {"status": status, "errors": errors, "complete_scenes": len(complete), "receipts": receipts}
    else:
        outcomes = {arm: np.asarray([by_scene[index][arm] for index in complete], dtype=np.float64) for arm in arms}
        seed = analysis["paired_bootstrap"]["seed"]
        draws = analysis["paired_bootstrap"]["draws"]
        comparisons = {}
        for offset, control in enumerate(("candidate0", "uniform_random", "critic_rerank")):
            delta = outcomes["visual_qgf"] - outcomes[control]
            comparisons[control] = {
                "mean_delta": float(delta.mean()),
                "bootstrap95": interval(delta, seed + offset, draws),
                "visual_only_success": int(np.sum((outcomes["visual_qgf"] == 1) & (outcomes[control] == 0))),
                "control_only_success": int(np.sum((outcomes["visual_qgf"] == 0) & (outcomes[control] == 1))),
            }
        admitted = (
            comparisons["candidate0"]["bootstrap95"][0] > 0
            and comparisons["uniform_random"]["bootstrap95"][0] > 0
            and comparisons["critic_rerank"]["bootstrap95"][0] >= -analysis["noninferiority_margin_vs_critic_rerank"]
        )
        status = "SIMPLEWAM_VISUAL_QGF_ONLINE_ADMIT" if admitted else "NO_SIMPLEWAM_VISUAL_QGF_ONLINE_BENEFIT"
        result = {
            "status": status, "complete_scenes": len(complete),
            "success": {arm: {"count": int(outcomes[arm].sum()), "rate": float(outcomes[arm].mean())} for arm in arms},
            "comparisons": comparisons, "receipts": receipts,
            "analysis_registration_sha256": sha256(analysis_path),
        }
    args.output.mkdir(parents=True, exist_ok=False)
    path = args.output / "REPORT.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / status).touch()
    print(json.dumps(result, indent=2))
    if status == "SIMPLEWAM_VISUAL_QGF_ONLINE_INCOMPLETE": raise SystemExit(2)


if __name__ == "__main__":
    main()
