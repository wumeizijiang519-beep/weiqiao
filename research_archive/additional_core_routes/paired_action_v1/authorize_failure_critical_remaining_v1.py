"""Authorize only the frozen remaining 15 groups after a clean pilot audit."""

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
    parser.add_argument("--pilot-manifest", type=Path, required=True)
    parser.add_argument("--pilot-manifest-sha256", required=True)
    parser.add_argument("--pilot-report", type=Path, required=True)
    parser.add_argument("--pilot-report-sha256", required=True)
    parser.add_argument("--pilot-audit", type=Path, required=True)
    parser.add_argument("--pilot-audit-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path, expected in ((args.pilot_manifest, args.pilot_manifest_sha256),
                           (args.pilot_report, args.pilot_report_sha256),
                           (args.pilot_audit, args.pilot_audit_sha256)):
        if sha(path) != expected:
            raise RuntimeError(f"Frozen authorization input changed: {path}")
    manifest = json.loads(args.pilot_manifest.read_text())
    pilot = json.loads(args.pilot_report.read_text())
    audit = json.loads(args.pilot_audit.read_text())
    if manifest.get("authorization_scope") != "PILOT_GROUP_0_ONLY":
        raise RuntimeError("Pilot authorization scope changed")
    if pilot.get("complete_groups") != 1 or pilot.get("entry_start") != 0 or pilot.get("entry_stop") != 1:
        raise RuntimeError("Pilot slice did not complete")
    if audit.get("status") != "FAILURE_CRITICAL_BOUNDARY_V1_PILOT_AUDIT_PASS":
        raise RuntimeError("Pilot audit did not pass")
    if audit.get("run_report_sha256") != args.pilot_report_sha256:
        raise RuntimeError("Pilot audit points to another report")
    authorized = dict(manifest)
    authorized.update({
        "authorization_scope": "REMAINING_GROUPS_1_THROUGH_15_ONLY",
        "authorization_received_at_cst": "2026-10-27T17:50:50+08:00",
        "authorization_source": "direct_user_message_in_qgf_causal_signal_v2_thread",
        "pilot_manifest_sha256": args.pilot_manifest_sha256,
        "pilot_report_sha256": args.pilot_report_sha256,
        "pilot_audit_sha256": args.pilot_audit_sha256,
        "entry_start": 1,
        "entry_stop": 16,
        "remaining_gpu_seconds_cap_including_failures": 13577,
        "pilot_gpu_seconds_charged": 823,
        "automatic_retry_allowed": False,
        "replacement_groups_allowed": False,
    })
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(authorized, indent=2, sort_keys=True))
    (args.output.parent / "AUTHORIZED_REMAINING_MANIFEST_SHA256").write_text(
        f"{sha(args.output)}  {args.output.name}\n")
    print(json.dumps({"status": authorized["status"],
                      "scope": authorized["authorization_scope"],
                      "entry_start": 1, "entry_stop": 16,
                      "remaining_gpu_seconds_cap": 13577}, indent=2))


if __name__ == "__main__":
    main()
