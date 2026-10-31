"""Fail-closed OOF qualification for Direct-Pairwise development."""

import argparse
import json
from pathlib import Path

import numpy as np


SEEDS = (202642301, 202642302, 202642303)
CONTROLS = ("state_only", "permutation", "action_only")
MODELS = ("proposed", *CONTROLS)
BOOTSTRAP_SEED = 202642601
BOOTSTRAP_DRAWS = 10000


def binary_loss(logits, target):
    return np.logaddexp(0.0, logits) - target * logits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    with np.load(args.corpus, allow_pickle=False) as frozen:
        frozen_group = frozen["group_index"].copy()
        frozen_target = frozen["target_scalar"].copy()
    expected_groups = set()
    for group in np.unique(frozen_group):
        values = frozen_target[frozen_group == group]
        if any(abs(float(values[left] - values[right])) > 1e-6
               for left in range(len(values)) for right in range(left + 1, len(values))):
            expected_groups.add(int(group))
    errors = []
    seed_reports = {}
    group_deltas = {control: [] for control in CONTROLS}

    for seed in SEEDS:
        rows = []
        for fold in range(3):
            run = args.execution / "runs" / f"seed_{seed}_fold_{fold}"
            if not (run / "WORKER_COMPLETE").exists():
                errors.append(f"incomplete worker {seed}/{fold}")
                continue
            report = json.loads((run / "REPORT.json").read_text())
            if (report.get("status") != "DIRECT_PAIRWISE_DEVELOPMENT_WORKER_COMPLETE"
                    or report.get("confirmation_labels_read") is not False
                    or report.get("updates") != 3000):
                errors.append(f"invalid worker receipt {seed}/{fold}")
                continue
            with np.load(run / "HELD_PREDICTIONS.npz", allow_pickle=False) as saved:
                required = {"target", "group_index", "left_index", "right_index", *MODELS}
                if set(saved.files) != required:
                    errors.append(f"prediction inventory {seed}/{fold}")
                    continue
                rows.append({key: saved[key].copy() for key in saved.files})
        if len(rows) != 3:
            continue
        payload = {key: np.concatenate([row[key] for row in rows]) for key in rows[0]}
        groups = payload["group_index"]
        covered = set(np.unique(groups).tolist())
        if covered != expected_groups:
            errors.append(f"seed {seed} unexpected informative-group inventory: {sorted(covered)}")
            continue
        group_losses = {name: [] for name in MODELS}
        group_ids = []
        for group in sorted(covered):
            mask = groups == group
            if not mask.any():
                continue
            group_ids.append(group)
            for name in MODELS:
                group_losses[name].append(float(binary_loss(payload[name][mask], payload["target"][mask]).mean()))
        improvements = {}
        proposed = np.asarray(group_losses["proposed"])
        for control in CONTROLS:
            delta = np.asarray(group_losses[control]) - proposed
            improvements[control] = float(delta.mean())
            group_deltas[control].append(delta)
        passes = all(value > 0.0 for value in improvements.values())
        seed_reports[str(seed)] = {
            "group_equal_log_loss": {name: float(np.mean(values)) for name, values in group_losses.items()},
            "improvement_vs_control": improvements,
            "informative_groups": group_ids,
            "passes": passes,
        }

    bootstrap = {}
    for control_index, control in enumerate(CONTROLS):
        values = group_deltas[control]
        if len(values) != 3:
            errors.append(f"missing seed deltas for {control}")
            continue
        group_mean = np.stack(values).mean(0)
        rng = np.random.default_rng(BOOTSTRAP_SEED + control_index)
        count = len(group_mean)
        sampled = group_mean[rng.integers(0, count, size=(BOOTSTRAP_DRAWS, count))].mean(1)
        lower, upper = np.quantile(sampled, [0.025, 0.975])
        bootstrap[control] = {
            "mean_improvement": float(group_mean.mean()),
            "ci95": [float(lower), float(upper)],
            "physical_groups": count,
            "passes": bool(lower > 0.0),
        }

    admitted = (
        not errors and len(seed_reports) == 3
        and all(report["passes"] for report in seed_reports.values())
        and len(bootstrap) == 3 and all(report["passes"] for report in bootstrap.values())
    )
    result = {
        "status": "DIRECT_PAIRWISE_DEVELOPMENT_ADMIT" if admitted else "NO_STABLE_DIRECT_PAIRWISE_DEVELOPMENT_CRITIC",
        "errors": errors,
        "seed_reports": seed_reports,
        "group_bootstrap": bootstrap,
        "bootstrap_seed_base": BOOTSTRAP_SEED,
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "informative_groups_from_frozen_corpus": sorted(expected_groups),
        "confirmation_labels_read": False,
        "online_qgf_efficacy_claim": False,
    }
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
