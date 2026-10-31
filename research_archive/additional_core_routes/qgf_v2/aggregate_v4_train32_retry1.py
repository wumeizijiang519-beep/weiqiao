#!/usr/bin/env python3
"""Aggregate the frozen QGF-v4 Train32 shards after the exact shard-3 retry."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


STAGE = Path("/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2")
OUT_DIR = STAGE / "v4_intervention_train32_v1"
SOURCES = [
    STAGE / "runs/v4_intervention_train32_shard0",
    STAGE / "runs/v4_intervention_train32_shard1",
    STAGE / "runs/v4_intervention_train32_shard2",
    STAGE / "runs/v4_intervention_train32_shard3_retry1",
]
FAILED_REPLACED_SOURCE = STAGE / "runs/v4_intervention_train32_shard3"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    output = OUT_DIR / "summary.json"
    complete = OUT_DIR / "COMPLETE"
    if output.exists() or complete.exists():
        raise FileExistsError(f"refusing to overwrite aggregate: {output}")

    audits = []
    audit_sources = []
    for source in SOURCES:
        marker = source / "COLLECTION_COMPLETE"
        audit_path = source / "audit.json"
        if not marker.exists() or not audit_path.exists():
            raise FileNotFoundError(f"incomplete shard: {source}")
        audit = json.loads(audit_path.read_text())
        if not audit.get("valid") or len(audit.get("episodes", [])) != 8:
            raise RuntimeError(f"invalid shard audit: {audit_path}")
        audits.append(audit)
        audit_sources.append(
            {
                "directory": str(source),
                "audit": str(audit_path),
                "audit_sha256": sha256(audit_path),
            }
        )

    episodes = [episode for audit in audits for episode in audit["episodes"]]
    seeds = [int(episode["seed"]) for episode in episodes]
    if len(episodes) != 32 or len(set(seeds)) != 32:
        raise RuntimeError("Train32 must contain exactly 32 unique episode seeds")

    for episode in episodes:
        trajectory = Path(episode["file"])
        if not trajectory.exists() or sha256(trajectory) != episode["sha256"]:
            raise RuntimeError(f"trajectory integrity failure: {trajectory}")

    successes = sum(int(bool(episode["success"])) for episode in episodes)
    failures = len(episodes) - successes
    valid = all(audit["valid"] for audit in audits) and len(episodes) == 32
    result = {
        "schema": "qgf_v4_randomized_intervention_train32",
        "valid": valid,
        "episodes": episodes,
        "successes": successes,
        "failures": failures,
        "shards": audits,
        "shard_sources": audit_sources,
        "replacement_provenance": {
            "failed_original_shard3": str(FAILED_REPLACED_SOURCE),
            "replacement_shard3": str(SOURCES[3]),
            "reason": "original shard3 renderer initialization failed before any accepted rollout",
        },
    }
    result["admits_critic_training"] = valid and successes >= 6 and failures >= 6

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n")
    os.replace(temporary, output)
    complete.touch()
    print(
        json.dumps(
            {key: result[key] for key in ("valid", "successes", "failures", "admits_critic_training")}
        )
    )


if __name__ == "__main__":
    main()
