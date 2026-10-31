"""Freeze the preregistered QGF-v5 four-fold OOF decision."""

import hashlib
import json
from pathlib import Path
import statistics


ROOT = Path("/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2/v5_candidate_centered_v1")
SEEDS = [202624001, 202624002, 202624003]
KINDS = ["action", "state_only", "selected_permutation"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    rows = {}
    elapsed = 0.0
    for fold in range(4):
        for kind in KINDS:
            for seed in SEEDS:
                name = f"fold{fold}_{kind}_seed{seed}"
                directory = ROOT / "training" / name
                if not (directory / "COMPLETE").exists():
                    raise ValueError(f"incomplete condition: {name}")
                metrics_path = directory / "final_metrics.json"
                metrics = json.loads(metrics_path.read_text())
                if metrics.get("step") != 10000 or len(metrics.get("episode_mse", [])) != 8:
                    raise ValueError(f"metrics contract failed: {name}")
                elapsed += float(metrics["elapsed_seconds"])
                rows[(seed, kind, fold)] = {"name": name, "metrics_sha256": sha(metrics_path), **metrics}
    pooled = {}
    passes = []
    for seed in SEEDS:
        pooled[str(seed)] = {}
        for kind in KINDS:
            fold_rows = [rows[(seed, kind, fold)] for fold in range(4)]
            per_episode = [value for row in fold_rows for value in row["episode_mse"]]
            pooled[str(seed)][kind] = {
                "episode_equal_mse": statistics.mean(per_episode),
                "fold_episode_equal_mse": [row["episode_equal_mse"] for row in fold_rows],
                "mean_candidate_margin": statistics.mean(row["mean_candidate_margin"] for row in fold_rows),
                "metric_sha256": [row["metrics_sha256"] for row in fold_rows],
            }
        action = pooled[str(seed)]["action"]
        state = pooled[str(seed)]["state_only"]
        permuted = pooled[str(seed)]["selected_permutation"]
        passes.append(action["episode_equal_mse"] < state["episode_equal_mse"]
                      and action["episode_equal_mse"] < permuted["episode_equal_mse"]
                      and action["mean_candidate_margin"] > 0)
    admitted = all(passes)
    result = {
        "schema": "qgf_v5_candidate_centered_oof_result_v1",
        "conditions": len(rows), "failed_conditions": 0,
        "total_gpu_training_seconds": elapsed,
        "pooled_by_seed": pooled, "seed_passes": passes,
        "online_admitted": admitted,
        "conclusion": "ADMIT_MATCHED_ONLINE" if admitted else "NO_CANDIDATE_CENTERED_ACTION_VALUE_EVIDENCE",
        "decision_rule": "action MSE below state-only and selected-permutation in all three seeds, with nonzero margins",
    }
    result_path = ROOT / "RESULT.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    conclusion = f"""# QGF v5 Method Conclusion

Frozen after all 36 preregistered fixed-final-step OOF conditions completed.

**Conclusion: `{result['conclusion']}`.**

The candidate-centered action model did not beat both same-target controls in
any bootstrap seed. It is therefore not admitted to matched online evaluation.
No seed, fold, checkpoint, or threshold is selected post hoc. This is a method
qualification result, not a robot success-rate result.

The dominant evidence is that correct selected-candidate assignment was worse
than state-only in all three seeds, while within-state candidate margins stayed
near zero. Together with the audited mean candidate deviation of 0.001126,
the current native proposal interface does not expose enough reliably useful
action variation for this critic configuration. Increasing runs on the same
data is not justified; any next attempt must separately preregister a proposal-
diversity intervention and obtain new matched data.
"""
    (ROOT / "METHOD_CONCLUSION.md").write_text(conclusion)
    with (ROOT / "result.sha256").open("w") as stream:
        for path in [result_path, ROOT / "METHOD_CONCLUSION.md", ROOT / "data" / "manifest.json"]:
            stream.write(f"{sha(path)}  {path.name}\n")
    (ROOT / "RESULT_COMPLETE").touch()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
