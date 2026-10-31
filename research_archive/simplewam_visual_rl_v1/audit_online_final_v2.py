"""Independent audit of the prospective 60-scene online V2 result."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
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
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "simplewam_visual_rl_v1"
    registration_path = base / "online_registration_v2_support_abstention/REGISTRATION.json"
    analysis_path = base / "online_analysis_registration_v2_support_abstention/REGISTRATION.json"
    execution = base / "online_execution_v2_support_abstention"
    registration = json.loads(registration_path.read_text())
    analysis = json.loads(analysis_path.read_text())
    final = json.loads((args.final / "REPORT.json").read_text())
    errors = []
    by_scene = defaultdict(dict)
    abstentions = defaultdict(int)
    decisions = defaultdict(int)
    for task in registration["tasks"]:
        folder = execution / f"task_{task['task_index']:03d}"
        report_path = folder / "REPORT.json"
        marker = folder / "SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE"
        if not report_path.exists() or not marker.exists():
            errors.append(f"missing task {task['task_index']}")
            continue
        report = json.loads(report_path.read_text())
        if report.get("scene_index") != task["scene_index"] or report.get("arm") != task["arm"]:
            errors.append(f"receipt mismatch {task['task_index']}")
            continue
        if report.get("online_registration_sha256") != sha256(registration_path):
            errors.append(f"registration mismatch {task['task_index']}")
        by_scene[task["scene_index"]][task["arm"]] = float(bool(report["official_success"]))
        for decision_path in sorted(folder.glob("transition_*/decision.json")):
            receipt = json.loads(decision_path.read_text())
            required = ("native_supported", "guided_supported", "support_abstention",
                        "selected_actions_sha256", "outcomes_read_for_selection")
            if any(key not in receipt for key in required):
                errors.append(f"decision receipt {decision_path}")
                continue
            if receipt["outcomes_read_for_selection"] != 0:
                errors.append(f"outcome read {decision_path}")
            decisions[task["arm"]] += 1
            abstentions[task["arm"]] += int(bool(receipt["support_abstention"]))
    expected_scenes = set(range(4, 64))
    arms = analysis["required_arms"]
    if set(by_scene) != expected_scenes or any(set(by_scene[index]) != set(arms) for index in expected_scenes):
        errors.append("scene-arm completeness")
    comparisons = {}
    if not errors:
        outcomes = {arm: np.asarray([by_scene[index][arm] for index in sorted(expected_scenes)]) for arm in arms}
        seed, draws = analysis["paired_bootstrap"]["seed"], analysis["paired_bootstrap"]["draws"]
        for offset, control in enumerate(("candidate0", "uniform_random", "critic_rerank")):
            delta = outcomes["visual_qgf"] - outcomes[control]
            comparisons[control] = {"mean_delta": float(delta.mean()),
                                    "bootstrap95": interval(delta, seed + offset, draws)}
            observed = final.get("comparisons", {}).get(control, {})
            if observed.get("mean_delta") != comparisons[control]["mean_delta"]:
                errors.append(f"mean mismatch {control}")
            if observed.get("bootstrap95") != comparisons[control]["bootstrap95"]:
                errors.append(f"bootstrap mismatch {control}")
    status = "SIMPLEWAM_VISUAL_QGF_ONLINE_V2_AUDIT_PASS" if not errors else "ONLINE_V2_AUDIT_FAILED"
    report = {"status": status, "errors": errors, "scenes": len(by_scene),
              "tasks": len(registration["tasks"]), "comparisons": comparisons,
              "support_abstention": {arm: {"count": abstentions[arm], "decisions": decisions[arm]}
                                      for arm in arms},
              "final_report_sha256": sha256(args.final / "REPORT.json")}
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / status).touch()
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
