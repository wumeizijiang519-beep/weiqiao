"""Independent structural audit of a frozen Runtime-Delta qualification report."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report_path = args.qualification / "REPORT.json"
    report = json.loads(report_path.read_text())
    errors = []
    if report.get("confirmation_labels_read") is not False:
        errors.append("confirmation seal violated")
    if report.get("bootstrap_draws") != 10000:
        errors.append("bootstrap draw count mismatch")
    if set(report.get("seed_reports", {})) != {"202642301", "202642302", "202642303"}:
        errors.append("seed inventory mismatch")
    controls = {"state_only", "permutation", "action_only"}
    for metric in ("component_mse", "pairwise_log_loss"):
        if set(report.get("group_bootstrap", {}).get(metric, {})) != controls:
            errors.append(f"bootstrap inventory mismatch for {metric}")
    expected_statuses = {"RUNTIME_DELTA_DEVELOPMENT_ADMIT", "NO_STABLE_RUNTIME_DELTA_DEVELOPMENT_CRITIC"}
    if report.get("status") not in expected_statuses:
        errors.append("unexpected qualification status")
    if not (args.qualification / report.get("status", "missing")).exists():
        errors.append("status marker missing")
    result = {
        "status": "RUNTIME_DELTA_QUALIFICATION_AUDIT_PASS" if not errors else "RUNTIME_DELTA_QUALIFICATION_AUDIT_FAIL",
        "errors": errors,
        "qualification_status": report.get("status"),
        "qualification_report_sha256": sha256(report_path),
    }
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
