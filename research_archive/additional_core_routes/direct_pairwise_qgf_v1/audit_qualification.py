"""Independent structural audit of Direct-Pairwise qualification."""

import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.qualification / "REPORT.json"
    report = json.loads(source.read_text())
    errors = []
    if report.get("confirmation_labels_read") is not False:
        errors.append("confirmation seal violated")
    if report.get("bootstrap_draws") != 10000:
        errors.append("bootstrap draw mismatch")
    if set(report.get("seed_reports", {})) != {"202642301", "202642302", "202642303"}:
        errors.append("seed inventory mismatch")
    if set(report.get("group_bootstrap", {})) != {"state_only", "permutation", "action_only"}:
        errors.append("control inventory mismatch")
    status = report.get("status")
    if status not in {"DIRECT_PAIRWISE_DEVELOPMENT_ADMIT", "NO_STABLE_DIRECT_PAIRWISE_DEVELOPMENT_CRITIC"}:
        errors.append("unexpected status")
    if not (args.qualification / str(status)).exists():
        errors.append("status marker missing")
    result = {
        "status": "DIRECT_PAIRWISE_QUALIFICATION_AUDIT_PASS" if not errors else "DIRECT_PAIRWISE_QUALIFICATION_AUDIT_FAIL",
        "errors": errors,
        "qualification_status": status,
        "qualification_report_sha256": sha(source),
    }
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
