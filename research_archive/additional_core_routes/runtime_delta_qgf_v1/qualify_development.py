"""Fail-closed OOF qualification for Runtime-Delta development predictions."""

import argparse
import json
from pathlib import Path

import numpy as np


SEEDS = (202642301, 202642302, 202642303)
CONTROLS = ("state_only", "permutation", "action_only")
MODELS = ("proposed", *CONTROLS)
BOOTSTRAP_SEED = 202642501
BOOTSTRAP_DRAWS = 10000
TIE_EPS = 1e-6


def pairwise_log_loss(scores, targets):
    losses = []
    for left in range(len(targets)):
        for right in range(left + 1, len(targets)):
            delta = float(targets[left] - targets[right])
            if abs(delta) <= TIE_EPS:
                continue
            signed_margin = np.sign(delta) * float(scores[left] - scores[right])
            losses.append(float(np.logaddexp(0.0, -signed_margin)))
    return float(np.mean(losses)) if losses else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    errors = []
    seed_reports = {}
    group_deltas = {
        metric: {control: [] for control in CONTROLS}
        for metric in ("component_mse", "pairwise_log_loss")
    }

    for seed in SEEDS:
        rows = []
        for fold in range(3):
            run = args.execution / "runs" / f"seed_{seed}_fold_{fold}"
            if not (run / "WORKER_COMPLETE").exists():
                errors.append(f"incomplete worker {seed}/{fold}")
                continue
            report = json.loads((run / "REPORT.json").read_text())
            if (report.get("status") != "RUNTIME_DELTA_DEVELOPMENT_WORKER_COMPLETE"
                    or report.get("confirmation_labels_read") is not False
                    or report.get("updates") != 3000):
                errors.append(f"invalid worker receipt {seed}/{fold}")
                continue
            with np.load(run / "HELD_PREDICTIONS.npz", allow_pickle=False) as saved:
                required = {
                    "target_components", "target_scalar", "group_index",
                    "candidate_index", "sensitivity", *MODELS,
                }
                if set(saved.files) != required:
                    errors.append(f"prediction inventory {seed}/{fold}")
                    continue
                rows.append({key: saved[key].copy() for key in saved.files})
        if len(rows) != 3:
            continue

        payload = {key: np.concatenate([row[key] for row in rows]) for key in rows[0]}
        groups = payload["group_index"]
        if set(np.unique(groups).tolist()) != set(range(24)):
            errors.append(f"seed {seed} lacks complete 24-group OOF coverage")
            continue
        if len(groups) != 192:
            errors.append(f"seed {seed} expected 192 rows, got {len(groups)}")
            continue
        if not np.allclose(payload["target_components"].mean(1), payload["target_scalar"], atol=1e-6, rtol=0):
            errors.append(f"seed {seed} target aggregation mismatch")
            continue

        group_metrics = {metric: {name: [] for name in MODELS}
                         for metric in ("component_mse", "pairwise_log_loss")}
        informative_groups = 0
        for group in range(24):
            mask = groups == group
            order = np.argsort(payload["candidate_index"][mask])
            if mask.sum() != 8 or not np.array_equal(payload["candidate_index"][mask][order], np.arange(8)):
                errors.append(f"seed {seed} invalid candidate bank for group {group}")
                continue
            target_components = payload["target_components"][mask][order]
            target_scalar = payload["target_scalar"][mask][order]
            group_pair_losses = {}
            for name in MODELS:
                prediction = payload[name][mask][order]
                group_metrics["component_mse"][name].append(
                    float(np.mean((prediction - target_components) ** 2))
                )
                loss = pairwise_log_loss(prediction.mean(1), target_scalar)
                group_pair_losses[name] = loss
            has_pairs = group_pair_losses["proposed"] is not None
            if any((loss is not None) != has_pairs for loss in group_pair_losses.values()):
                errors.append(f"seed {seed} inconsistent pair inventory for group {group}")
                continue
            if has_pairs:
                informative_groups += 1
                for name, loss in group_pair_losses.items():
                    group_metrics["pairwise_log_loss"][name].append(loss)
        if informative_groups == 0:
            errors.append(f"seed {seed} has no informative groups")
            continue

        improvements = {metric: {} for metric in group_metrics}
        means = {metric: {} for metric in group_metrics}
        for metric in group_metrics:
            proposed = np.asarray(group_metrics[metric]["proposed"], dtype=np.float64)
            means[metric]["proposed"] = float(proposed.mean())
            for control in CONTROLS:
                control_values = np.asarray(group_metrics[metric][control], dtype=np.float64)
                means[metric][control] = float(control_values.mean())
                delta = control_values - proposed
                improvements[metric][control] = float(delta.mean())
                group_deltas[metric][control].append(delta)
        passes = all(
            improvements[metric][control] > 0.0
            for metric in improvements for control in CONTROLS
        )
        seed_reports[str(seed)] = {
            "group_equal_metrics": means,
            "improvement_vs_control": improvements,
            "mean_action_sensitivity": float(np.mean(payload["sensitivity"])),
            "informative_groups": informative_groups,
            "passes": passes,
        }

    bootstrap = {metric: {} for metric in group_deltas}
    for metric_index, metric in enumerate(group_deltas):
        for control_index, control in enumerate(CONTROLS):
            values = group_deltas[metric][control]
            if len(values) != 3:
                errors.append(f"missing seed deltas for {metric}/{control}")
                continue
            group_mean = np.stack(values).mean(0)
            rng = np.random.default_rng(BOOTSTRAP_SEED + 10 * metric_index + control_index)
            group_count = len(group_mean)
            sampled = group_mean[
                rng.integers(0, group_count, size=(BOOTSTRAP_DRAWS, group_count))
            ].mean(1)
            lower, upper = np.quantile(sampled, [0.025, 0.975])
            bootstrap[metric][control] = {
                "mean_improvement": float(group_mean.mean()),
                "ci95": [float(lower), float(upper)],
                "physical_groups": group_count,
                "passes": bool(lower > 0.0),
            }

    admitted = (
        not errors
        and len(seed_reports) == 3
        and all(report["passes"] for report in seed_reports.values())
        and all(
            bootstrap[metric].get(control, {}).get("passes", False)
            for metric in bootstrap for control in CONTROLS
        )
    )
    result = {
        "status": "RUNTIME_DELTA_DEVELOPMENT_ADMIT" if admitted else "NO_STABLE_RUNTIME_DELTA_DEVELOPMENT_CRITIC",
        "errors": errors,
        "seed_reports": seed_reports,
        "group_bootstrap": bootstrap,
        "bootstrap_seed_base": BOOTSTRAP_SEED,
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "tie_epsilon": TIE_EPS,
        "confirmation_labels_read": False,
        "online_qgf_efficacy_claim": False,
    }
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
