"""Freeze all 32 prospective V2 group authorizations before execution."""

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
    if manifest["status"] != "PROGRESS_PAIRWISE_QGF_V2_PROSPECTIVE_REGISTERED" or len(manifest["entries"]) != 32:
        raise RuntimeError("V2 manifest is not frozen")
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for index, source_entry in enumerate(manifest["entries"]):
        entry = dict(source_entry)
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
                actual = int(data["actual_length"])
                if actual != receipt["actual_length"]:
                    raise RuntimeError("Transition length changed")
                actions.extend(np.asarray(data["executed_actions"][:actual], dtype=np.float32))
        prefix = np.stack(actions)
        if prefix.shape != (entry["boundary_model_step"], 7):
            raise RuntimeError("Authorized prefix shape changed")
        entry["prefix_actions_sha256"] = hashlib.sha256(prefix.tobytes()).hexdigest()
        value = {"status": "PROGRESS_PAIRWISE_QGF_V2_GROUP_AUTHORIZED",
                 "manifest_sha256": sha(args.manifest), "entry_index": index,
                 "episode_config_sha256": sha(config_path),
                 "entry": entry, "v2_split": entry["v2_split"]}
        path = args.output / f"entry_{index:02d}.json"
        path.write_text(json.dumps(value, indent=2, sort_keys=True))
        rows.append({"entry_index": index, "authorization_sha256": sha(path),
                     "episode_id": entry["episode_id"], "v2_split": entry["v2_split"]})
    result = {"status": "PROGRESS_PAIRWISE_QGF_V2_32_GROUPS_AUTHORIZED",
              "manifest_sha256": sha(args.manifest), "groups": rows,
              "gpu_seconds_cap": 28800, "replacement_allowed": False}
    (args.output / "MANIFEST.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
