"""Freeze the V2 development groups under the runtime-anchored contract."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2-manifest", type=Path, required=True)
    parser.add_argument("--v2-support-bases", type=Path, required=True)
    parser.add_argument("--v2-authorization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    v2 = json.loads(args.v2_manifest.read_text())
    selected = [dict(row) for row in v2["entries"] if row["v2_split"] == "development"]
    if len(selected) != 16 or len({row["physical_input_group"] for row in selected}) != 16:
        raise RuntimeError("Frozen V2 development population changed")
    v2_by_group = {}
    v2_auth_paths = {}
    for path in args.v2_authorization.glob("entry_*.json"):
        auth = json.loads(path.read_text())
        group = auth["entry"]["physical_input_group"]
        v2_by_group[group] = auth
        v2_auth_paths[group] = path
    entries = []
    for source in selected:
        authorization = v2_by_group.get(source["physical_input_group"])
        if authorization is None:
            raise RuntimeError("Missing frozen V2 authorization")
        enriched = dict(authorization["entry"])
        for key, value in source.items():
            if enriched.get(key) != value:
                raise RuntimeError(f"V2 authorization changed {key}")
        for key in ("task_name", "state_sha256", "prefix_actions_sha256"):
            if not isinstance(enriched.get(key), str) or len(enriched[key]) != 64 and key != "task_name":
                raise RuntimeError(f"Missing execution receipt {key}")
        entries.append(enriched)
    for runtime_index, entry in enumerate(entries):
        entry["runtime_anchored_index"] = runtime_index
    args.output.mkdir(parents=True, exist_ok=False)
    basis = args.output / "SUPPORT_BASES.npz"
    shutil.copyfile(args.v2_support_bases, basis)
    if sha(basis) != v2["support_bases_sha256"]:
        raise RuntimeError("Support basis changed")
    manifest = {
        "status": "RUNTIME_ANCHORED_QGF_V1_REGISTERED",
        "groups": 16,
        "pilot_index": 0,
        "entries": entries,
        "support": v2["support"],
        "source_v2_manifest_sha256": sha(args.v2_manifest),
        "support_bases_sha256": sha(basis),
        "selection_rule": "all_v2_development_groups_in_manifest_order",
        "selection_reads_v2_candidate_outcomes": False,
        "validation_or_formal_read": False,
        "replacement_allowed": False,
        "bootstrap_seed": 202642201,
        "bootstrap_draws": 10000,
    }
    manifest_path = args.output / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    auth_dir = args.output / "authorization"
    auth_dir.mkdir()
    for index, entry in enumerate(entries):
        source = v2_by_group.get(entry["physical_input_group"])
        if source is None:
            raise RuntimeError(f"Missing frozen authorization for group {index}")
        authorization = {
            "status": "RUNTIME_ANCHORED_QGF_V1_GROUP_AUTHORIZED",
            "entry_index": index,
            "manifest_sha256": sha(manifest_path),
            "source_v2_authorization_sha256": sha(v2_auth_paths[entry["physical_input_group"]]),
            "entry": entry,
        }
        (auth_dir / f"entry_{index:02d}.json").write_text(
            json.dumps(authorization, indent=2, sort_keys=True))
    (args.output / "SHA256SUMS").write_text(
        f"{sha(manifest_path)}  MANIFEST.json\n{sha(basis)}  SUPPORT_BASES.npz\n")


if __name__ == "__main__":
    main()
