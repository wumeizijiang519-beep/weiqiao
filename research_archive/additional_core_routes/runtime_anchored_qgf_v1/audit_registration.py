"""Independent audit of the runtime-anchored prospective registration."""

import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--v2-manifest", type=Path, required=True)
    parser.add_argument("--v2-support-bases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.registration / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    v2 = json.loads(args.v2_manifest.read_text())
    errors = []
    expected = [row for row in v2["entries"] if row["v2_split"] == "development"]
    actual = manifest.get("entries", [])
    if len(expected) != 16 or len(actual) != 16:
        errors.append("development population is not 16")
    for index, (source, registered) in enumerate(zip(expected, actual)):
        for key, value in source.items():
            if registered.get(key) != value:
                errors.append(f"entry {index} changed field {key}")
        if registered.get("runtime_anchored_index") != index:
            errors.append(f"entry {index} runtime index mismatch")
        auth_path = args.registration / "authorization" / f"entry_{index:02d}.json"
        auth = json.loads(auth_path.read_text())
        if (auth.get("status") != "RUNTIME_ANCHORED_QGF_V1_GROUP_AUTHORIZED"
                or auth.get("entry_index") != index
                or auth.get("manifest_sha256") != sha(manifest_path)
                or auth.get("entry") != registered):
            errors.append(f"entry {index} authorization mismatch")
    if sha(args.registration / "SUPPORT_BASES.npz") != sha(args.v2_support_bases):
        errors.append("support bases are not byte-identical")
    if manifest.get("selection_reads_v2_candidate_outcomes") is not False:
        errors.append("outcome-independent selection receipt missing")
    result = {
        "status": "RUNTIME_ANCHORED_REGISTRATION_AUDIT_PASS" if not errors else
                  "RUNTIME_ANCHORED_REGISTRATION_AUDIT_FAIL",
        "errors": errors,
        "groups": len(actual),
        "manifest_sha256": sha(manifest_path),
        "support_bases_sha256": sha(args.registration / "SUPPORT_BASES.npz"),
        "v2_candidate_outcomes_read": False,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
