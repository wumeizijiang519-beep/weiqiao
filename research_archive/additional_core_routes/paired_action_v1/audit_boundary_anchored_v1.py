"""Independent audit of a finalized boundary-anchored paired intervention."""

import argparse
import hashlib
import json
from pathlib import Path

from boundary_anchored_metrics import qualify


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--remaining", type=Path, required=True)
    parser.add_argument("--population", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    final_path = args.final / "REPORT.json"
    report = json.loads(final_path.read_text())
    population = json.loads(args.population.read_text())
    expected = [row["episode_id"] for row in population["entries"]]
    rows = report["results"]
    errors = []
    if [row["episode_id"] for row in rows] != expected:
        errors.append("Final rows do not match the frozen population order")
    if len(rows) != 16 or len(set(expected)) != 16:
        errors.append("Population is not exactly 16 unique groups")

    source_by_episode = {}
    for root in (args.pilot, args.remaining):
        source = json.loads((root / "REPORT.json").read_text())
        for row in source["results"]:
            if row["episode_id"] in source_by_episode:
                errors.append(f"Duplicate source result: {row['episode_id']}")
            source_by_episode[row["episode_id"]] = (root, row)

    max_commit_error = 0.0
    for row in rows:
        source_root, source_row = source_by_episode.get(row["episode_id"], (None, None))
        if source_row != row:
            errors.append(f"Source/final row mismatch: {row['episode_id']}")
            continue
        group = source_root / row["episode_id"]
        if row["status"] == "PAIRED_GROUP_COMPLETE":
            if not (group / "GROUP_COMPLETE").is_file():
                errors.append(f"Missing GROUP_COMPLETE: {row['episode_id']}")
            if not (group / "frozen_policy_input.npz").is_file():
                errors.append(f"Missing frozen policy input: {row['episode_id']}")
            if {branch["candidate_index"] for branch in row["branches"]} != {0, 1, 2, 3}:
                errors.append(f"Candidate coverage mismatch: {row['episode_id']}")
            for branch in row["branches"]:
                max_commit_error = max(max_commit_error, float(branch["commit_max_error"]))
                branch_dir = group / f"candidate_{branch['candidate_index']}"
                for name, key in (("trajectory.npz", "trajectory_sha256"),
                                  ("rollout.mp4", "video_sha256")):
                    path = branch_dir / name
                    if not path.is_file() or sha(path) != branch[key]:
                        errors.append(f"Bad {name}: {row['episode_id']}/{branch['candidate_index']}")
        elif row["status"] == "GROUP_UNAVAILABLE":
            if not (group / "FAILED.txt").is_file():
                errors.append(f"Missing failure evidence: {row['episode_id']}")
        else:
            errors.append(f"Unknown row status: {row['status']}")

    if max_commit_error > 1e-6:
        errors.append(f"Commit error exceeded threshold: {max_commit_error}")
    recalculated = qualify(rows)
    for key, value in recalculated.items():
        if report.get(key) != value:
            errors.append(f"Qualification mismatch: {key}")

    result = {
        "status": "BOUNDARY_ANCHORED_INDEPENDENT_AUDIT_PASS" if not errors
                  else "BOUNDARY_ANCHORED_INDEPENDENT_AUDIT_FAIL",
        "final_report_sha256": sha(final_path),
        "complete_groups": recalculated["complete_groups"],
        "qualification_status": recalculated["status"],
        "max_commit_error": max_commit_error,
        "errors": errors,
        "qgf_efficacy_claim": False,
    }
    args.output.mkdir(exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        raise SystemExit("; ".join(errors))
    (args.output / "AUDIT_PASS").touch()


if __name__ == "__main__":
    main()
