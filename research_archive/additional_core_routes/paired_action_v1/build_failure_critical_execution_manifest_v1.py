"""Enrich the audited cohort with immutable runtime fields without authorizing GPU work."""

import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--cohort-sha256", required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--audit-sha256", required=True)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path, expected in ((args.cohort, args.cohort_sha256),
                           (args.audit, args.audit_sha256)):
        if sha(path) != expected:
            raise RuntimeError(f"Frozen input changed: {path}")
    cohort = json.loads(args.cohort.read_text())
    audit = json.loads(args.audit.read_text())
    if cohort["status"] != "FAILURE_CRITICAL_BOUNDARY_V1_COHORT_PROPOSED_NOT_AUTHORIZED":
        raise RuntimeError("Unexpected cohort status")
    if audit["status"] != "FAILURE_CRITICAL_BOUNDARY_V1_COHORT_AUDIT_PASS":
        raise RuntimeError("Independent cohort audit did not pass")
    if audit.get("gpu_execution_authorized") is not False:
        raise RuntimeError("Cohort audit authorization field changed")
    entries = []
    for entry in cohort["entries"]:
        summary_path = Path(entry["episode_directory"]) / "summary.json"
        if sha(summary_path) != entry["summary_sha256"]:
            raise RuntimeError("Certified episode summary changed")
        summary = json.loads(summary_path.read_text())
        enriched = dict(entry)
        enriched["task_name"] = summary["task_name"]
        enriched["state_sha256"] = summary["state_sha256"]
        entries.append(enriched)
    result = {
        "status": "FAILURE_CRITICAL_BOUNDARY_V1_EXECUTION_READY_AWAITING_AUTHORIZATION",
        "gpu_execution_authorized": False,
        "cohort_sha256": args.cohort_sha256,
        "cohort_audit_sha256": args.audit_sha256,
        "runner_sha256": sha(args.runner),
        "protocol_sha256": sha(args.protocol),
        "entries": entries,
        "groups": 16,
        "pilot_group_index": 0,
        "candidate_seeds": [10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000],
        "candidate_horizon": 32,
        "pilot_release_requires": {
            "complete_groups": 1,
            "branches": 8,
            "unique_candidates": 8,
            "commit_max_error": 1e-6,
            "clean_process_exit": True,
        },
        "final_gate": {
            "complete_groups": 12,
            "binary_discordant_groups": 4,
            "binary_families": 2,
            "dense_bootstrap_families": 2,
            "bootstrap_draws": 10000,
            "bootstrap_seed": 202641401,
        },
        "gpu_seconds_cap_including_failures": 14400,
        "automatic_retry_allowed": False,
        "replacement_groups_allowed": False,
        "qgf_efficacy_claim": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output.parent / "EXECUTION_MANIFEST_SHA256").write_text(
        f"{sha(args.output)}  {args.output.name}\n")
    print(json.dumps({"status": result["status"], "groups": len(entries),
                      "gpu_execution_authorized": False}, indent=2))


if __name__ == "__main__":
    main()
