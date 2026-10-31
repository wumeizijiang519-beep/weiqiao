"""Freeze the four-observation QGF-v6 zero-action diversity decision."""

import hashlib
import json
from pathlib import Path
import statistics


ROOT = Path("/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2/v6_diverse_bank_v1")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    reports = []
    for index in range(4):
        attempt = "zero_action_gate_retry2" if index == 0 else "zero_action_gate_retry3"
        directory = ROOT / attempt / f"observation{index}"
        if not (directory / "COMPLETE").exists():
            raise ValueError(f"incomplete observation {index}")
        report = json.loads((directory / "report.json").read_text())
        report["report_sha256"] = sha(directory / "report.json")
        reports.append(report)
    ratios = [row["diversity_ratio"] for row in reports]
    valid = all(row["all_finite"] and row["subset_nonidentical"] and row["candidate0_preserved"]
                and row["selected_commit_max_error"] <= 1e-6 for row in reports)
    admitted = valid and statistics.median(ratios) >= 2.0
    result = {
        "schema": "qgf_v6_zero_action_gate_result_v1", "observations": 4,
        "diversity_ratios": ratios, "median_diversity_ratio": statistics.median(ratios),
        "max_commit_error": max(row["selected_commit_max_error"] for row in reports),
        "valid_contract": valid, "intervention_pilot_admitted": admitted,
        "conclusion": "ADMIT_RANDOMIZED_INTERVENTION_PILOT" if admitted else "DIVERSE_BANK_GATE_FAILED",
        "reports": reports,
    }
    path = ROOT / "ZERO_ACTION_RESULT.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    (ROOT / "zero_action_result.sha256").write_text(f"{sha(path)}  {path.name}\n")
    (ROOT / "ZERO_ACTION_GATE_COMPLETE").touch()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
