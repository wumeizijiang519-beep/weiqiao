"""Validate the complete four-shard UNITAS latent export."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    manifests = []
    for rank in range(4):
        if not (args.output / ("SHARD_%d_COMPLETE" % rank)).exists():
            raise ValueError("missing shard completion")
        manifests.append(json.loads((args.output / ("manifest_rank%d.json" % rank)).read_text()))
    rows = [row for manifest in manifests for row in manifest["episodes"]]
    if len(rows) != 60 or len({row["seed"] for row in rows}) != 60:
        raise ValueError("latent population must contain 60 unique seeds")
    expected = {int(row["seed"]): row for row in audit["episodes"]}
    if set(expected) != {int(row["seed"]) for row in rows}:
        raise ValueError("latent seeds differ from source audit")
    for row in rows:
        seed = int(row["seed"])
        if row["source_sha256"] != expected[seed]["sha256"]:
            raise ValueError("source SHA mismatch")
        path = args.output / ("seed_%d.npz" % seed)
        if sha256(path) != row["latent_sha256"]:
            raise ValueError("latent SHA mismatch")
        data = np.load(path, allow_pickle=False)
        latent = data["latent_states"]
        if latent.shape != (int(row["observations"]), 9216) or not np.isfinite(latent).all():
            raise ValueError("invalid latent array")
    summary = {
        "schema": "qgf_v3_unitas_latents_complete_v1",
        "episodes": 60,
        "successes": sum(bool(row["success"]) for row in rows),
        "failures": sum(not bool(row["success"]) for row in rows),
        "frames": sum(int(row["observations"]) for row in rows),
        "feature_dim": 9216,
        "source_audit_sha256": sha256(args.audit),
        "total_gpu_forward_seconds": sum(float(row["elapsed_seconds"]) for row in rows),
    }
    (args.output / "manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.output / "COMPLETE").write_text("\n")


if __name__ == "__main__":
    main()
