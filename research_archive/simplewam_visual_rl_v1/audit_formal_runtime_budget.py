#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[int(fraction * (len(ordered) - 1))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    historical = root / "online_execution_v2_support_abstention"
    registration_path = root / "formal_online_registration_v1" / "REGISTRATION.json"
    registration = json.loads(registration_path.read_text())
    values = []
    receipts = []
    for path in sorted(historical.glob("task_*/REPORT.json")):
        document = json.loads(path.read_text())
        # Runtime budgeting deliberately does not read official_success or feedback.
        task_index = int(document["task_index"])
        wall_seconds = float(document["wall_seconds"])
        if not math.isfinite(wall_seconds) or wall_seconds <= 0:
            raise SystemExit("invalid historical wall time")
        values.append(wall_seconds)
        receipts.append({"task_index": task_index, "report_sha256": sha256(path), "wall_seconds": wall_seconds})
    if len(values) != 240 or len(registration.get("tasks", [])) != 412:
        raise SystemExit("runtime evidence cardinality mismatch")
    lanes = 4
    tasks_per_lane = math.ceil(412 / lanes)
    mean_seconds = sum(values) / len(values)
    p90_seconds = percentile(values, 0.90)
    mean_makespan_hours = tasks_per_lane * mean_seconds / 3600.0
    p90_makespan_hours = tasks_per_lane * p90_seconds / 3600.0
    deadline = datetime(2026, 10, 31, 24 % 24, 0, 0, tzinfo=timezone(timedelta(hours=8))) + timedelta(days=1)
    safety_hours = 1.0
    latest_safe_start = deadline - timedelta(hours=p90_makespan_hours + safety_hours)
    output = {
        "status": "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_RUNTIME_BUDGET_AUDIT_PASS",
        "historical_partition": "consumed_validation_runtime_only",
        "historical_tasks": len(values),
        "historical_outcomes_read": 0,
        "formal_registration_sha256": sha256(registration_path),
        "formal_tasks": 412,
        "lanes": lanes,
        "tasks_per_lane_ceiling": tasks_per_lane,
        "historical_wall_seconds": {
            "minimum": min(values),
            "mean": mean_seconds,
            "median": percentile(values, 0.50),
            "p90": p90_seconds,
            "maximum": max(values),
        },
        "projection": {
            "mean_makespan_hours": mean_makespan_hours,
            "p90_task_time_makespan_hours": p90_makespan_hours,
            "mean_gpu_hours": 412 * mean_seconds / 3600.0,
            "safety_margin_hours": safety_hours,
            "platform_deadline_cst": deadline.isoformat(),
            "latest_safe_four_gpu_start_cst": latest_safe_start.isoformat(),
        },
        "receipts": receipts,
    }
    output_dir = root / "formal_runtime_budget_v1"
    output_dir.mkdir(parents=True, exist_ok=False)
    report_path = output_dir / "REPORT.json"
    report_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    (output_dir / output["status"]).write_text("\n")
    print(json.dumps({key: value for key, value in output.items() if key != "receipts"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
