"""Materialize the user's explicit one-pilot authorization without altering science."""

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
    parser.add_argument("--ready-manifest", type=Path, required=True)
    parser.add_argument("--ready-manifest-sha256", required=True)
    parser.add_argument("--ready-audit", type=Path, required=True)
    parser.add_argument("--ready-audit-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path, expected in ((args.ready_manifest, args.ready_manifest_sha256),
                           (args.ready_audit, args.ready_audit_sha256)):
        if sha(path) != expected:
            raise RuntimeError(f"Frozen authorization input changed: {path}")
    manifest = json.loads(args.ready_manifest.read_text())
    audit = json.loads(args.ready_audit.read_text())
    if manifest["status"] != "FAILURE_CRITICAL_BOUNDARY_V1_EXECUTION_READY_AWAITING_AUTHORIZATION":
        raise RuntimeError("Unexpected ready-manifest status")
    if audit["status"] != "FAILURE_CRITICAL_BOUNDARY_V1_EXECUTION_READY_AUDIT_PASS":
        raise RuntimeError("Execution-ready audit did not pass")
    if audit["manifest_sha256"] != args.ready_manifest_sha256:
        raise RuntimeError("Audit points to a different manifest")
    authorized = dict(manifest)
    authorized.update({
        "status": "FAILURE_CRITICAL_BOUNDARY_V1_REGISTERED_AND_AUTHORIZED",
        "gpu_execution_authorized": True,
        "authorization_scope": "PILOT_GROUP_0_ONLY",
        "authorization_received_at_cst": "2026-10-27T17:00:00+08:00",
        "authorization_source": "direct_user_message_in_qgf_causal_signal_v2_thread",
        "ready_manifest_sha256": args.ready_manifest_sha256,
        "ready_audit_sha256": args.ready_audit_sha256,
        "remaining_groups_authorized_before_pilot_release": False,
    })
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(authorized, indent=2, sort_keys=True))
    (args.output.parent / "AUTHORIZED_MANIFEST_SHA256").write_text(
        f"{sha(args.output)}  {args.output.name}\n")
    print(json.dumps({"status": authorized["status"],
                      "scope": authorized["authorization_scope"],
                      "groups": len(authorized["entries"])}, indent=2))


if __name__ == "__main__":
    main()
