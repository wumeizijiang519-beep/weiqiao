"""Independent recomputation of the frozen visual-IQL qualification gate."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def lower95(values, seed):
    generator = np.random.default_rng(seed)
    indices = generator.integers(len(values), size=(10000, len(values)))
    return float(np.quantile(values[indices].mean(1), 0.025))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    claimed = json.loads(args.qualification.read_text())
    errors, recomputed = [], {}
    for seed in (202644201, 202644202, 202644203):
        parts = []
        for fold in (0, 1, 2):
            path = args.execution / f"seed_{seed}_fold_{fold}" / "HELDOUT_PREDICTIONS.npz"
            with np.load(path, allow_pickle=False) as archive:
                parts.append({key: archive[key] for key in archive.files})
        merged = {key: np.concatenate([part[key] for part in parts]) for key in parts[0]}
        if sorted(merged["row_index"].tolist()) != list(range(len(merged["row_index"]))):
            errors.append(f"seed {seed} does not contain exactly one OOF prediction per row")
        groups = sorted(set(merged["group"].tolist()))
        controls = {}
        for offset, control in enumerate(("state_only", "permutation")):
            deltas = []
            for group in groups:
                mask = merged["group"] == group
                target = merged["target_return"][mask]
                proposed_mse = np.mean((merged["proposed"][mask] - target) ** 2)
                control_mse = np.mean((merged[control][mask] - target) ** 2)
                deltas.append(control_mse - proposed_mse)
            values = np.asarray(deltas)
            controls[control] = {
                "group_mean_mse_improvement": float(values.mean()),
                "bootstrap_lower95": lower95(values, 202644301 + seed % 1000 + offset),
            }
        sensitivity = float(np.mean(np.abs(merged["proposed"] - merged["proposed_shuffled"])))
        state_sensitivity = float(np.mean(np.abs(merged["state_only"] - merged["state_only_shuffled"])))
        permutation_sensitivity = float(np.mean(np.abs(merged["permutation"] - merged["permutation_shuffled"])))
        passed = all(value["bootstrap_lower95"] > 0 for value in controls.values()) and sensitivity >= 1e-3 and sensitivity > max(state_sensitivity, permutation_sensitivity)
        recomputed[str(seed)] = {
            "controls": controls, "action_sensitivity": sensitivity,
            "state_only_action_sensitivity": state_sensitivity,
            "permutation_action_sensitivity": permutation_sensitivity, "pass": passed,
        }
        original = claimed.get("seeds", {}).get(str(seed), {})
        if original.get("pass") != passed:
            errors.append(f"seed {seed} pass mismatch")
        for control in controls:
            for metric in controls[control]:
                if not np.isclose(controls[control][metric], original.get("controls", {}).get(control, {}).get(metric, np.nan), rtol=0, atol=1e-12):
                    errors.append(f"seed {seed} {control} {metric} mismatch")
    if claimed.get("status") != "SIMPLEWAM_VISUAL_IQL_QUALIFIED":
        errors.append("qualification did not claim pass")
    if not all(result["pass"] for result in recomputed.values()):
        errors.append("not every seed independently passes")
    status = "SIMPLEWAM_VISUAL_IQL_QUALIFICATION_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_IQL_QUALIFICATION_AUDIT_FAILED"
    report = {
        "status": status, "errors": errors, "seeds": recomputed,
        "qualification_report_sha256": sha256(args.qualification), "draws": 10000,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2))
    (args.output / status).touch()
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
