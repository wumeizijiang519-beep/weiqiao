"""Qualify the frozen three-seed OOF Simple-WAM visual IQL critic."""

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


def bootstrap_lower(values, seed, draws=10000):
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(values), size=(draws, len(values)))
    means = values[sampled].mean(axis=1)
    return float(np.quantile(means, 0.025)), float(values.mean())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--registrations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.registrations / "MANIFEST.json").read_text())
    errors, seed_results = [], {}
    for item in manifest["workers"]:
        worker = item["worker"]
        run = args.execution / worker
        report_path = run / "REPORT.json"
        if not report_path.exists():
            errors.append(f"missing report: {worker}")
            continue
        report = json.loads(report_path.read_text())
        if report.get("status") != "SIMPLEWAM_VISUAL_IQL_WORKER_COMPLETE":
            errors.append(f"worker incomplete: {worker}")
            continue
        if report.get("registration_sha256") != item["sha256"]:
            errors.append(f"registration receipt mismatch: {worker}")
        if sha256(run / "HELDOUT_PREDICTIONS.npz") != report.get("predictions_sha256"):
            errors.append(f"prediction hash mismatch: {worker}")
        for variant, metrics in report["metrics"].items():
            if sha256(run / f"{variant}.pt") != metrics.get("checkpoint_sha256"):
                errors.append(f"checkpoint hash mismatch: {worker}/{variant}")
        seed_results.setdefault(str(report["seed"]), []).append(run / "HELDOUT_PREDICTIONS.npz")
    qualification = {}
    all_pass = not errors and len(seed_results) == 3
    for seed_text, paths in sorted(seed_results.items()):
        merged = {}
        for path in paths:
            with np.load(path, allow_pickle=False) as archive:
                for key in archive.files:
                    merged.setdefault(key, []).append(archive[key])
        merged = {key: np.concatenate(value) for key, value in merged.items()}
        if len(set(merged["row_index"].tolist())) != len(merged["row_index"]):
            errors.append(f"duplicate OOF rows for seed {seed_text}")
        groups = sorted(set(merged["group"].tolist()))
        group_deltas = {"state_only": [], "permutation": []}
        for group in groups:
            mask = merged["group"] == group
            proposed_error = np.mean((merged["proposed"][mask] - merged["target_return"][mask]) ** 2)
            for control in group_deltas:
                control_error = np.mean((merged[control][mask] - merged["target_return"][mask]) ** 2)
                group_deltas[control].append(control_error - proposed_error)
        seed = int(seed_text)
        controls = {}
        for offset, (control, values) in enumerate(group_deltas.items()):
            lower, mean = bootstrap_lower(np.asarray(values), 202644301 + seed % 1000 + offset)
            controls[control] = {"group_mean_mse_improvement": mean, "bootstrap_lower95": lower}
        sensitivity = float(np.mean(np.abs(merged["proposed"] - merged["proposed_shuffled"])))
        state_sensitivity = float(np.mean(np.abs(merged["state_only"] - merged["state_only_shuffled"])))
        permutation_sensitivity = float(np.mean(np.abs(merged["permutation"] - merged["permutation_shuffled"])))
        passed = (
            all(item["bootstrap_lower95"] > 0 for item in controls.values())
            and sensitivity >= 1e-3
            and sensitivity > state_sensitivity
            and sensitivity > permutation_sensitivity
        )
        qualification[seed_text] = {
            "rows": len(merged["row_index"]), "physical_groups": len(groups),
            "controls": controls,
            "action_sensitivity": sensitivity,
            "state_only_action_sensitivity": state_sensitivity,
            "permutation_action_sensitivity": permutation_sensitivity,
            "pass": passed,
        }
        all_pass = all_pass and passed
    status = "SIMPLEWAM_VISUAL_IQL_QUALIFIED" if all_pass and not errors else "NO_STABLE_SIMPLEWAM_VISUAL_IQL_CRITIC"
    result = {
        "status": status, "errors": errors, "seeds": qualification,
        "draws": 10000, "group_equal": True,
        "manifest_sha256": sha256(args.registrations / "MANIFEST.json"),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2))
    (args.output / status).touch()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
