"""Independent zero-GPU audit of the complete 288-episode visual export."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    registration = json.loads(args.registration.read_text())
    dataset = json.loads(Path(registration["dataset_result"]).read_text())
    index = json.loads(Path(registration["input_index"]).read_text())
    entries = {row["episode_id"]: row for row in dataset["entries"]}
    inputs = {row["episode_id"]: row for row in index["episodes"]}
    errors: list[str] = []
    total_observations = 0
    position_hash = None
    blocks = args.export / "blocks"
    if len(entries) != 288 or set(entries) != set(inputs):
        errors.append("registered population is not the frozen 288")
    for episode_id in sorted(entries):
        receipt_path = blocks / f"{episode_id}.json"
        feature_path = blocks / f"{episode_id}.npz"
        if not receipt_path.is_file() or not feature_path.is_file():
            errors.append(f"missing block {episode_id}")
            continue
        receipt = json.loads(receipt_path.read_text())
        expected_hashes = inputs[episode_id]["observation_file_sha256"]
        if receipt.get("observation_sha256") != expected_hashes:
            errors.append(f"input receipt mismatch {episode_id}")
        if receipt.get("feature_file_sha256") != sha(feature_path):
            errors.append(f"feature file hash mismatch {episode_id}")
        try:
            with np.load(feature_path, allow_pickle=False) as archive:
                if set(archive.files) != {"features", "positions"}:
                    raise ValueError("unexpected arrays")
                features = np.asarray(archive["features"])
                positions = np.asarray(archive["positions"])
            if features.shape != (len(expected_hashes), 8, 3072) or features.dtype != np.float32:
                raise ValueError("feature shape/dtype")
            if positions.shape != (8, 5) or positions.dtype != np.float32:
                raise ValueError("position shape/dtype")
            if not np.isfinite(features).all() or not np.isfinite(positions).all():
                raise ValueError("nonfinite arrays")
            if not np.all(positions[:, 2] == 0) or set(positions[:, 1].tolist()) != {-1.0, 1.0}:
                raise ValueError("current-frame/two-camera contract")
            current_position_hash = hashlib.sha256(np.ascontiguousarray(positions).tobytes()).hexdigest()
            if position_hash is None:
                position_hash = current_position_hash
            elif position_hash != current_position_hash:
                raise ValueError("position grid changed")
            total_observations += len(features)
        except Exception as exc:
            errors.append(f"invalid {episode_id}: {exc}")
    report = {
        "status": "SIMPLEWAM_VISUAL_FEATURE_EXPORT_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_FEATURE_EXPORT_AUDIT_FAIL",
        "errors": errors,
        "episodes": len(entries) - sum(error.startswith("missing block") for error in errors),
        "observations": total_observations,
        "feature_shape_per_observation": [8, 3072],
        "position_sha256": position_hash,
        "registration_sha256": sha(args.registration),
        "export_report_sha256": sha(args.export / "REPORT.json") if (args.export / "REPORT.json").is_file() else None,
        "robot_actions_executed": 0,
        "critic_updates": 0,
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2))
    if errors:
        raise RuntimeError(f"feature export audit failed with {len(errors)} errors")
    (args.output / report["status"]).touch()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
