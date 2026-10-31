"""CPU-only audit of the registered raw-byte initial-state hashes."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    registration = json.loads(args.registration.read_text())
    cache = {}
    rows = []
    for entry in registration["entries"]:
        path = Path(entry["initial_state_path"])
        if path not in cache:
            cache[path] = np.asarray(torch.load(path, map_location="cpu", weights_only=False))
        states = cache[path]
        if "_add_" in path.name or "_level" in path.name:
            states = states.reshape(1, -1)
        initial = np.asarray(states[entry["initial_state_index"]], dtype="<f8")
        actual = hashlib.sha256(initial.tobytes()).hexdigest()
        row = {
            "episode_id": entry["episode_id"],
            "initial_state_path": str(path),
            "initial_state_index": entry["initial_state_index"],
            "expected_sha256": entry["state_sha256"],
            "actual_raw_bytes_sha256": actual,
            "match": actual == entry["state_sha256"],
        }
        rows.append(row)
        if not row["match"]:
            raise RuntimeError(f"Initial state mismatch for {entry['episode_id']}")
    report = {
        "status": "ALL_16_INITIAL_STATE_RAW_HASHES_PASS",
        "entries": len(rows),
        "unique_state_files": len(cache),
        "hash_operation": "sha256(np.asarray(state, dtype='<f8').tobytes())",
        "gpu_seconds": 0,
        "rows": rows,
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / "ALL_16_INITIAL_STATE_RAW_HASHES_PASS").touch()
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
