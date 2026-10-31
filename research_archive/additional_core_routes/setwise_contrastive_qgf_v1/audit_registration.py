"""Independently audit the prospective setwise cohort and receipts."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def groups(path):
    data = json.loads(Path(path).read_text())
    return {row["physical_input_group"] for row in data["entries"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--failure-critical", type=Path, required=True)
    parser.add_argument("--v1-manifest", type=Path, required=True)
    parser.add_argument("--v2-manifest", type=Path, required=True)
    parser.add_argument("--reference-support", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=False)
    manifest_path = args.registration / "MANIFEST.json"
    support_path = args.registration / "SUPPORT_BASES.npz"
    manifest = json.loads(manifest_path.read_text())
    authorization = json.loads((args.authorization / "MANIFEST.json").read_text())
    errors = []
    rows = manifest.get("entries", [])
    selected = [row.get("physical_input_group") for row in rows]
    prior = groups(args.failure_critical) | groups(args.v1_manifest) | groups(args.v2_manifest)
    if len(prior) != 64:
        errors.append("prior union is not exactly 64 groups")
    if len(rows) != 24 or len(set(selected)) != 24:
        errors.append("registration is not 24 unique groups")
    if set(selected) & prior:
        errors.append("prospective cohort overlaps prior interventions")
    split_family = Counter((row.get("setwise_split"), row.get("family")) for row in rows)
    families = sorted({row.get("family") for row in rows})
    if len(families) != 4:
        errors.append("cohort does not contain four families")
    for split in ("development", "confirmation"):
        for family in families:
            if split_family[(split, family)] != 3:
                errors.append(f"{split}/{family} does not contain three groups")
    if sha(support_path) != sha(args.reference_support):
        errors.append("support basis is not byte-identical to V1")
    if authorization.get("manifest_sha256") != sha(manifest_path):
        errors.append("authorization references the wrong manifest")
    receipts = authorization.get("groups", [])
    if len(receipts) != 24 or sorted(row.get("entry_index") for row in receipts) != list(range(24)):
        errors.append("authorization does not cover all 24 entries")
    for receipt in receipts:
        index = int(receipt["entry_index"])
        path = args.authorization / f"entry_{index:02d}.json"
        if not path.exists() or sha(path) != receipt.get("authorization_sha256"):
            errors.append(f"authorization receipt mismatch for entry {index}")
            continue
        value = json.loads(path.read_text())
        authorized_entry = value.get("entry", {})
        if any(authorized_entry.get(key) != item for key, item in rows[index].items()):
            errors.append(f"registered field changed in authorization entry {index}")
        for key in ("task_name", "state_sha256", "prefix_actions_sha256"):
            if not isinstance(authorized_entry.get(key), str) or not authorized_entry[key]:
                errors.append(f"authorization field {key} missing for entry {index}")
        if value.get("status") != "RUNTIME_ANCHORED_QGF_V1_GROUP_AUTHORIZED":
            errors.append(f"unexpected authorization status for entry {index}")
    report = {
        "status": "SETWISE_CONTRASTIVE_REGISTRATION_AUDIT_PASS" if not errors else "SETWISE_CONTRASTIVE_REGISTRATION_AUDIT_FAIL",
        "errors": errors,
        "groups": len(rows),
        "prior_groups": len(prior),
        "families": families,
        "split_family_counts": {f"{key[0]}::{key[1]}": value for key, value in sorted(split_family.items())},
        "manifest_sha256": sha(manifest_path),
        "authorization_manifest_sha256": sha(args.authorization / "MANIFEST.json"),
        "support_bases_sha256": sha(support_path),
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(2)
    (args.output / "SETWISE_CONTRASTIVE_REGISTRATION_AUDIT_PASS").touch()


if __name__ == "__main__":
    main()
