"""Qualify complete development OOF predictions before confirmation is opened."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


SEEDS = (202642301, 202642302, 202642303)
CONTROLS = ("state_only", "permutation", "independent")
BOOTSTRAP_SEED = 202642401
BOOTSTRAP_DRAWS = 10000
SENSITIVITY_MIN = 1e-3


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def binary_loss(logits, target):
    return np.logaddexp(0.0, logits) - target * logits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    errors = []
    seed_reports = {}
    group_delta_by_control = {name: [] for name in CONTROLS}
    for seed in SEEDS:
        rows = []
        sensitivities = []
        for fold in range(3):
            run = args.execution / "runs" / f"seed_{seed}_fold_{fold}"
            if not (run / "WORKER_COMPLETE").exists():
                errors.append(f"incomplete worker {seed}/{fold}")
                continue
            report = json.loads((run / "REPORT.json").read_text())
            if report.get("status") != "SETWISE_DEVELOPMENT_WORKER_COMPLETE" or report.get("confirmation_labels_read") is not False:
                errors.append(f"invalid worker receipt {seed}/{fold}")
                continue
            with np.load(run / "HELD_PREDICTIONS.npz", allow_pickle=False) as saved:
                required = {"target", "group_index", "sensitivity", "setwise", *CONTROLS}
                if set(saved.files) != required:
                    errors.append(f"prediction inventory {seed}/{fold}")
                    continue
                payload = {key: saved[key].copy() for key in saved.files}
            rows.append(payload)
            sensitivities.extend(payload["sensitivity"].tolist())
        if len(rows) != 3:
            continue
        target = np.concatenate([row["target"] for row in rows])
        group = np.concatenate([row["group_index"] for row in rows])
        prediction = {name: np.concatenate([row[name] for row in rows]) for name in ("setwise", *CONTROLS)}
        if set(np.unique(group).tolist()) != set(range(12)):
            errors.append(f"seed {seed} lacks complete group OOF coverage")
            continue
        group_losses = {name: [] for name in prediction}
        for physical_group in range(12):
            mask = group == physical_group
            if not mask.any():
                errors.append(f"seed {seed} empty group {physical_group}")
                continue
            for name in prediction:
                group_losses[name].append(float(binary_loss(prediction[name][mask], target[mask]).mean()))
        improvements = {
            control: float(np.mean(group_losses[control]) - np.mean(group_losses["setwise"]))
            for control in CONTROLS
        }
        for control in CONTROLS:
            group_delta_by_control[control].append(
                np.asarray(group_losses[control]) - np.asarray(group_losses["setwise"])
            )
        sensitivity = float(np.mean(sensitivities))
        passed = all(value > 0.0 for value in improvements.values()) and sensitivity >= SENSITIVITY_MIN
        seed_reports[str(seed)] = {
            "group_equal_loss": {name: float(np.mean(value)) for name, value in group_losses.items()},
            "improvement_vs_control": improvements,
            "mean_cyclic_action_sensitivity": sensitivity,
            "passes": passed,
        }
    bootstrap = {}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    for control in CONTROLS:
        values = group_delta_by_control[control]
        if len(values) != 3:
            errors.append(f"missing seed deltas for {control}")
            continue
        group_mean = np.stack(values).mean(axis=0)
        sampled = group_mean[rng.integers(0, 12, size=(BOOTSTRAP_DRAWS, 12))].mean(axis=1)
        lower, upper = np.quantile(sampled, [0.025, 0.975])
        bootstrap[control] = {
            "mean_improvement": float(group_mean.mean()),
            "ci95": [float(lower), float(upper)],
            "passes": bool(lower > 0.0),
        }
    admitted = (
        not errors
        and len(seed_reports) == 3
        and all(report["passes"] for report in seed_reports.values())
        and len(bootstrap) == 3
        and all(report["passes"] for report in bootstrap.values())
    )
    result = {
        "status": "SETWISE_DEVELOPMENT_CRITIC_ADMIT" if admitted else "NO_STABLE_SETWISE_DEVELOPMENT_CRITIC",
        "errors": errors,
        "seed_reports": seed_reports,
        "group_bootstrap": bootstrap,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "sensitivity_min": SENSITIVITY_MIN,
        "confirmation_labels_read": False,
        "qgf_efficacy_claim": False,
    }
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
