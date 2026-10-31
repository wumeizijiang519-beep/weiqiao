"""Independent consistency audit for the frozen Retry 2 paired diagnostic."""

import argparse
import hashlib
import json
from pathlib import Path


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--process-exit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report_path = args.run / "REPORT.json"
    report = json.loads(report_path.read_text())
    registration = json.loads(args.registration.read_text())
    expected = {row["episode_id"] for row in registration["entries"]}
    rows = report["results"]
    observed = [row["episode_id"] for row in rows]
    errors = []

    if len(rows) != 16 or len(set(observed)) != 16 or set(observed) != expected:
        errors.append("The report does not cover the frozen 16 episodes exactly once")
    if args.process_exit.read_text().strip() != "0":
        errors.append("Retry 2 process did not exit cleanly")

    complete = 0
    unavailable = 0
    differing = 0
    families = set()
    failure_classes = {}
    for row in rows:
        group = args.run / row["episode_id"]
        if row["status"] == "PAIRED_GROUP_COMPLETE":
            complete += 1
            if not (group / "GROUP_COMPLETE").is_file():
                errors.append(f"{row['episode_id']}: missing GROUP_COMPLETE")
            branches = row.get("branches", [])
            if {branch.get("candidate_index") for branch in branches} != {0, 1, 2, 3}:
                errors.append(f"{row['episode_id']}: candidate coverage is not 0..3")
            successes = set()
            for branch in branches:
                branch_dir = group / f"candidate_{branch['candidate_index']}"
                for name, key in (("trajectory.npz", "trajectory_sha256"),
                                  ("rollout.mp4", "video_sha256")):
                    artifact = branch_dir / name
                    if not artifact.is_file() or file_sha(artifact) != branch.get(key):
                        errors.append(f"{row['episode_id']}: bad {name} receipt")
                successes.add(bool(branch.get("success")))
            calculated = len(successes) > 1
            if calculated != bool(row.get("differing_binary_outcome")):
                errors.append(f"{row['episode_id']}: binary discordance mismatch")
            if calculated:
                differing += 1
                families.add(row["family"])
        elif row["status"] == "GROUP_UNAVAILABLE":
            unavailable += 1
            failed = group / "FAILED.txt"
            if not failed.is_file() or failed.read_text() != row.get("error"):
                errors.append(f"{row['episode_id']}: failure evidence mismatch")
            last = row.get("error", "").strip().splitlines()[-1]
            failure_classes[last] = failure_classes.get(last, 0) + 1
        else:
            errors.append(f"{row['episode_id']}: unknown status {row['status']}")

    admitted = complete >= 12 and differing >= 4 and len(families) >= 2
    expected_status = "PAIRED_SIGNAL_GATE_PASS" if admitted else "NO_IDENTIFIABLE_SIGNAL"
    checks = {
        "complete_groups": complete,
        "unavailable_groups": unavailable,
        "differing_binary_groups": differing,
        "differing_families": sorted(families),
        "calculated_status": expected_status,
    }
    for key, value in checks.items():
        if report.get(key if key != "calculated_status" else "status") != value:
            errors.append(f"report field mismatch: {key}")

    output = {
        "status": "INDEPENDENT_AUDIT_PASS" if not errors else "INDEPENDENT_AUDIT_FAIL",
        "frozen_result": expected_status,
        "report_sha256": file_sha(report_path),
        "checks": checks,
        "failure_classes": failure_classes,
        "errors": errors,
        "qgf_efficacy_claim": False,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(output, indent=2, sort_keys=True))
    if errors:
        raise SystemExit("; ".join(errors))
    (args.output / "AUDIT_PASS").touch()


if __name__ == "__main__":
    main()
