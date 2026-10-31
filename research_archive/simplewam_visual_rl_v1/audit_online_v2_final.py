"""Independently audit the frozen Online V2 result from task receipts."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def bootstrap(delta: np.ndarray, seed: int, draws: int):
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, delta.size, size=(draws, delta.size))
    means = delta[indices].mean(axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = args.root / "simplewam_visual_rl_v1"
    registration_path = base / "online_registration_v2_support_abstention/REGISTRATION.json"
    analysis_path = base / "online_analysis_registration_v2_support_abstention/REGISTRATION.json"
    final_path = base / "online_final_v2_support_abstention/REPORT.json"
    execution = base / "online_execution_v2_support_abstention"
    registration = json.loads(registration_path.read_text())
    analysis = json.loads(analysis_path.read_text())
    frozen = json.loads(final_path.read_text())

    arms = analysis["required_arms"]
    expected_scenes = analysis["scene_indices"]
    outcomes = {scene: {} for scene in expected_scenes}
    receipt_hashes = {}
    errors = []

    if len(registration["tasks"]) != len(expected_scenes) * len(arms):
        errors.append("registration task count mismatch")
    if digest(registration_path) != analysis["online_registration_sha256"]:
        errors.append("online registration hash mismatch")

    for task in registration["tasks"]:
        index = task["task_index"]
        folder = execution / f"task_{index:03d}"
        report_path = folder / "REPORT.json"
        marker = folder / "SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE"
        if not report_path.is_file() or not marker.is_file():
            errors.append(f"missing complete receipt {index}")
            continue
        report = json.loads(report_path.read_text())
        expected = (index, task["scene_index"], task["arm"])
        actual = (report.get("task_index"), report.get("scene_index"), report.get("arm"))
        if actual != expected or report.get("status") != "SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE":
            errors.append(f"receipt mismatch {index}")
            continue
        if report.get("online_registration_sha256") != digest(registration_path):
            errors.append(f"registration receipt mismatch {index}")
        outcomes[task["scene_index"]][task["arm"]] = int(bool(report["official_success"]))
        receipt_hashes[index] = digest(report_path)

    if any(set(values) != set(arms) for values in outcomes.values()):
        errors.append("incomplete four-arm scene")

    success = {}
    comparisons = {}
    if not errors:
        vectors = {
            arm: np.asarray([outcomes[scene][arm] for scene in expected_scenes], dtype=np.float64)
            for arm in arms
        }
        success = {
            arm: {"count": int(values.sum()), "rate": float(values.mean())}
            for arm, values in vectors.items()
        }
        seed = analysis["paired_bootstrap"]["seed"]
        draws = analysis["paired_bootstrap"]["draws"]
        for offset, control in enumerate(("candidate0", "uniform_random", "critic_rerank")):
            delta = vectors["visual_qgf"] - vectors[control]
            comparisons[control] = {
                "mean_delta": float(delta.mean()),
                "bootstrap95": bootstrap(delta, seed + offset, draws),
                "visual_only_success": int(np.sum((vectors["visual_qgf"] == 1) & (vectors[control] == 0))),
                "control_only_success": int(np.sum((vectors["visual_qgf"] == 0) & (vectors[control] == 1))),
            }

    if success != frozen.get("success"):
        errors.append("success summary mismatch")
    if comparisons != frozen.get("comparisons"):
        errors.append("comparison summary mismatch")
    frozen_receipts = {row["task_index"]: row["report_sha256"] for row in frozen.get("receipts", [])}
    if receipt_hashes != frozen_receipts:
        errors.append("receipt hash set mismatch")

    admitted = False
    if not errors:
        admitted = (
            comparisons["candidate0"]["bootstrap95"][0] > 0
            and comparisons["uniform_random"]["bootstrap95"][0] > 0
            and comparisons["critic_rerank"]["bootstrap95"][0]
            >= -analysis["noninferiority_margin_vs_critic_rerank"]
        )
        expected_status = (
            "SIMPLEWAM_VISUAL_QGF_ONLINE_ADMIT"
            if admitted
            else "NO_SIMPLEWAM_VISUAL_QGF_ONLINE_BENEFIT"
        )
        if frozen.get("status") != expected_status:
            errors.append("frozen status mismatch")

    status = (
        "SIMPLEWAM_VISUAL_QGF_ONLINE_V2_FINAL_AUDIT_PASS"
        if not errors
        else "SIMPLEWAM_VISUAL_QGF_ONLINE_V2_FINAL_AUDIT_FAIL"
    )
    result = {
        "status": status,
        "errors": errors,
        "complete_tasks": len(receipt_hashes),
        "complete_scenes": len(expected_scenes),
        "admitted": admitted,
        "scientific_status": frozen.get("status"),
        "success": success,
        "comparisons": comparisons,
        "online_registration_sha256": digest(registration_path),
        "analysis_registration_sha256": digest(analysis_path),
        "final_report_sha256": digest(final_path),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / status).touch()
    print(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
