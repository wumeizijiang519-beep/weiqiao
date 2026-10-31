"""Add the omitted frozen V1 support metadata without rebuilding the cohort."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--v1-manifest", type=Path, required=True)
    parser.add_argument("--original-bases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original = json.loads(args.original.read_text())
    v1 = json.loads(args.v1_manifest.read_text())
    if (original["status"] != "PROGRESS_PAIRWISE_QGF_V2_PROSPECTIVE_REGISTERED"
            or original["groups"] != 32 or "support" in original):
        raise RuntimeError("Unexpected original V2 metadata state")
    if sha(args.original_bases) != original["v1_support_bases_sha256"]:
        raise RuntimeError("V2 support basis receipt changed")
    repaired = dict(original)
    repaired["support"] = v1["support"]
    repaired["support_bases_sha256"] = original["v1_support_bases_sha256"]
    repaired["metadata_repair"] = {
        "kind": "copy frozen V1 support statistics and standard basis-hash alias only",
        "original_manifest_sha256": sha(args.original),
        "v1_manifest_sha256": sha(args.v1_manifest),
        "selection_or_split_changed": False,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = args.output / "MANIFEST.json"
    manifest.write_text(json.dumps(repaired, indent=2, sort_keys=True))
    shutil.copyfile(args.original_bases, args.output / "SUPPORT_BASES.npz")
    (args.output / "SHA256SUMS").write_text(
        f"{sha(manifest)}  MANIFEST.json\n{sha(args.output / 'SUPPORT_BASES.npz')}  SUPPORT_BASES.npz\n")
    print(json.dumps(repaired["metadata_repair"], indent=2))


if __name__ == "__main__": main()
