"""Create the immutable pilot authorization from frozen local receipts."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--entry-index", type=int, default=0)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if not 0 <= args.entry_index < 16:
        raise RuntimeError("Entry index outside frozen population")
    entry = dict(manifest["entries"][args.entry_index])
    archive = Path(entry["episode_directory"])
    config_path = archive / "config.json"
    config = json.loads(config_path.read_text())
    if config.get("episode_id") != entry["episode_id"]:
        raise RuntimeError("Episode identity receipt changed")
    for key in ("task_name", "state_sha256"):
        entry[key] = config[key]
    actions = []
    for receipt in entry["transition_receipts"]:
        path = archive / f"transition_{receipt['index']:04d}/transition.npz"
        if sha(path) != receipt["sha256"]:
            raise RuntimeError("Transition receipt changed")
        with np.load(path, allow_pickle=False) as data:
            actions.extend(np.asarray(data["executed_actions"][:int(data["actual_length"])],
                                      dtype=np.float32))
    prefix = np.stack(actions)
    if prefix.shape != (entry["boundary_model_step"], 7):
        raise RuntimeError("Authorized prefix shape changed")
    entry["prefix_actions_sha256"] = hashlib.sha256(prefix.tobytes()).hexdigest()
    result = {
        "status": "PROGRESS_PAIRWISE_QGF_V1_PILOT_AUTHORIZED",
        "scope": "FIXED_SINGLE_ENTRY",
        "entry_index": args.entry_index,
        "manifest_sha256": sha(args.manifest),
        "episode_config_sha256": sha(config_path),
        "entry": entry,
        "pilot_hard_seconds": 1800,
        "automatic_retry_policy": "ONE_MINIMAL_INFRASTRUCTURE_RETRY_WITHIN_UNCHANGED_BUDGET",
        "scientific_retry_policy": "FORBIDDEN",
        "qgf_efficacy_claim": False,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
