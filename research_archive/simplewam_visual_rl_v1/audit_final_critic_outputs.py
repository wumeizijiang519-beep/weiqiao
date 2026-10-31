#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
from pathlib import Path


SEEDS = [202644201, 202644202, 202644203]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    manifest_path = root / "final_critic_registrations_v1" / "MANIFEST.json"
    output_dir = root / "final_critic_audit_v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    errors = []
    manifest = json.loads(manifest_path.read_text())
    workers = manifest.get("workers", [])
    if [int(item.get("seed", -1)) for item in workers] != SEEDS:
        errors.append("manifest seed order mismatch")
    audited = []
    for item in workers:
        seed = int(item["seed"])
        registration_path = Path(item["registration"])
        registration_sha = sha256(registration_path)
        if registration_sha != item.get("sha256"):
            errors.append("seed %d registration hash mismatch" % seed)
        registration = json.loads(registration_path.read_text())
        run_dir = root / "final_critic_execution_v1" / ("seed_%d" % seed)
        report_path = run_dir / "REPORT.json"
        checkpoint_path = run_dir / "FINAL_CRITIC.pt"
        marker_path = run_dir / "SIMPLEWAM_VISUAL_IQL_FINAL_COMPLETE"
        for path in (report_path, checkpoint_path, marker_path):
            if not path.exists():
                errors.append("seed %d missing %s" % (seed, path.name))
        if not report_path.exists() or not checkpoint_path.exists():
            continue
        report = json.loads(report_path.read_text())
        checkpoint_sha = sha256(checkpoint_path)
        checks = {
            "registration_seed": registration.get("seed") == seed,
            "all_training_rows_registered": registration.get("uses_all_training_rows") is True,
            "no_heldout_fold": registration.get("heldout_fold") is None,
            "no_validation_or_online_outcomes": registration.get("validation_or_online_outcomes_read") == 0,
            "registered_rows": registration.get("required_rows") == 12218,
            "registered_updates": registration.get("training", {}).get("updates") == 50000,
            "registered_batch": registration.get("training", {}).get("batch_size") == 64,
            "report_status": report.get("status") == "SIMPLEWAM_VISUAL_IQL_FINAL_COMPLETE",
            "report_seed": report.get("seed") == seed,
            "report_rows": report.get("training_rows") == 12218,
            "report_step": report.get("fixed_final_step") == 50000,
            "registration_hash_link": report.get("registration_sha256") == registration_sha,
            "checkpoint_hash_link": report.get("checkpoint_sha256") == checkpoint_sha,
            "metrics_not_selection_inputs": report.get("metrics_are_checkpoint_selection_inputs") is False,
        }
        metrics = report.get("metrics", {})
        numeric_metrics = ["loss", "q_loss", "v_loss", "q_mean", "q_std", "mc_mse_full_training", "action_sensitivity_full_training"]
        checks["metrics_finite"] = all(isinstance(metrics.get(key), (int, float)) and math.isfinite(metrics[key]) for key in numeric_metrics)
        checks["action_sensitivity_nonzero"] = metrics.get("action_sensitivity_full_training", 0.0) > 0.0
        checks["q_std_nonzero"] = metrics.get("q_std", 0.0) > 0.0
        failed = sorted(key for key, value in checks.items() if not value)
        if failed:
            errors.append("seed %d failed checks: %s" % (seed, ",".join(failed)))
        audited.append({
            "seed": seed,
            "registration_sha256": registration_sha,
            "report_sha256": sha256(report_path),
            "checkpoint_sha256": checkpoint_sha,
            "fixed_final_step": report.get("fixed_final_step"),
            "training_rows": report.get("training_rows"),
            "metrics": metrics,
            "checks": checks,
        })
    if len(audited) != 3:
        errors.append("expected 3 audited workers, got %d" % len(audited))
    status = "SIMPLEWAM_VISUAL_IQL_FINAL_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_IQL_FINAL_AUDIT_FAIL"
    output = {
        "status": status,
        "errors": errors,
        "manifest_sha256": sha256(manifest_path),
        "ensemble_rule": "mean_over_three_seeds_of_min_q1_q2",
        "outcome_dependent_selection": False,
        "workers": audited,
    }
    report_out = output_dir / "REPORT.json"
    report_out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    if not errors:
        (output_dir / status).write_text("\n")
    print(status)
    print("REPORT_SHA256=" + sha256(report_out))
    if errors:
        for error in errors:
            print("ERROR=" + error)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
