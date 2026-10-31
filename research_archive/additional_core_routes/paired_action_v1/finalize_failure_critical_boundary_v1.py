"""Combine the non-overlapping pilot and remaining slices and freeze the gate."""

import argparse
import hashlib
import json
from pathlib import Path

from failure_critical_metrics_v1 import qualify


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--remaining", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pilot_path = args.pilot / "REPORT.json"
    remaining_path = args.remaining / "REPORT.json"
    pilot = json.loads(pilot_path.read_text())
    remaining = json.loads(remaining_path.read_text())
    authorization = json.loads(args.authorization.read_text())
    if (pilot.get("entry_start"), pilot.get("entry_stop")) != (0, 1):
        raise RuntimeError("Pilot slice changed")
    if (remaining.get("entry_start"), remaining.get("entry_stop")) != (1, 16):
        raise RuntimeError("Remaining slice changed")
    if authorization.get("authorization_scope") != "REMAINING_GROUPS_1_THROUGH_15_ONLY":
        raise RuntimeError("Remaining authorization scope changed")
    if sha(pilot_path) != authorization["pilot_report_sha256"]:
        raise RuntimeError("Pilot report changed")
    rows = pilot["results"] + remaining["results"]
    episodes = [row["episode_id"] for row in rows]
    if len(rows) != 16 or len(set(episodes)) != 16:
        raise RuntimeError("Combined population is not 16 unique groups")
    qualification = qualify(rows)
    result = {**qualification,
              "unavailable_groups": 16 - qualification["complete_groups"],
              "pilot_report_sha256": sha(pilot_path),
              "remaining_report_sha256": sha(remaining_path),
              "authorization_sha256": sha(args.authorization),
              "population_episode_ids": episodes,
              "qgf_efficacy_claim": False,
              "results": rows}
    args.output.mkdir(exist_ok=False)
    report = args.output / "REPORT.json"
    report.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()
    print(json.dumps({key: result[key] for key in ("status", "complete_groups", "unavailable_groups")}, indent=2))


if __name__ == "__main__":
    main()
