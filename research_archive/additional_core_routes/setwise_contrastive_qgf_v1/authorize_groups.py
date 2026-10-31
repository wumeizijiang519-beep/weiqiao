"""Freeze all 24 group execution receipts before GPU work."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("branch_contract") != "SETWISE_CONTRASTIVE_QGF_V1" or len(manifest["entries"]) != 24:
        raise RuntimeError("Unexpected setwise manifest")
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for index, source in enumerate(manifest["entries"]):
        entry = dict(source)
        archive = Path(entry["episode_directory"])
        config_path = archive / "config.json"
        config = json.loads(config_path.read_text())
        if config["episode_id"] != entry["episode_id"]:
            raise RuntimeError("Episode identity changed")
        entry["task_name"] = config["task_name"]
        entry["state_sha256"] = config["state_sha256"]
        actions = []
        for receipt in entry["transition_receipts"]:
            path = archive / f"transition_{receipt['index']:04d}/transition.npz"
            if sha(path) != receipt["sha256"]:
                raise RuntimeError("Transition receipt changed")
            with np.load(path, allow_pickle=False) as data:
                actual = int(data["actual_length"])
                actions.extend(np.asarray(data["executed_actions"][:actual], dtype=np.float32))
        prefix = np.stack(actions)
        if prefix.shape != (entry["boundary_model_step"], 7):
            raise RuntimeError("Prefix shape changed")
        entry["prefix_actions_sha256"] = hashlib.sha256(prefix.tobytes()).hexdigest()
        value = {"status": "RUNTIME_ANCHORED_QGF_V1_GROUP_AUTHORIZED",
                 "branch_contract": "SETWISE_CONTRASTIVE_QGF_V1",
                 "manifest_sha256": sha(args.manifest), "entry_index": index,
                 "episode_config_sha256": sha(config_path), "entry": entry}
        path = args.output / f"entry_{index:02d}.json"
        path.write_text(json.dumps(value, indent=2, sort_keys=True))
        rows.append({"entry_index": index, "authorization_sha256": sha(path),
                     "split": entry["setwise_split"], "episode_id": entry["episode_id"]})
    result = {"status": "SETWISE_CONTRASTIVE_24_GROUPS_AUTHORIZED",
              "manifest_sha256": sha(args.manifest), "groups": rows,
              "gpu_seconds_cap": 21600, "replacement_allowed": False}
    (args.output / "MANIFEST.json").write_text(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
