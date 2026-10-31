"""Independent zero-GPU audit of the Simple-WAM visual feature pilot."""

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
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report_path = args.pilot / "REPORT.json"
    feature_path = args.pilot / "FEATURES.npz"
    report = json.loads(report_path.read_text())
    errors: list[str] = []
    expected = {
        "status": "SIMPLEWAM_VISUAL_FEATURE_PILOT_PASS",
        "backbone": "Simple-WAM",
        "benchmark": "LIBERO",
        "tau0_runtime_dependency": False,
        "feature_spec": {"layers": [29], "spatial_stride": 4, "num_views": 2},
        "grid_size": [3, 7, 14],
        "feature_shape": [1, 8, 3072],
        "position_shape": [8, 5],
        "robot_actions_executed": 0,
        "critic_updates": 0,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            errors.append(f"unexpected {key}")
    if report.get("repeat_max_abs_error") != 0.0 or report.get("position_repeat_max_abs_error") != 0.0:
        errors.append("pilot was not bitwise repeatable")
    observation = Path(report.get("observation", ""))
    if not observation.is_file() or sha(observation) != report.get("observation_sha256"):
        errors.append("frozen observation receipt mismatch")
    try:
        with np.load(feature_path, allow_pickle=False) as archive:
            if set(archive.files) != {"features", "positions"}:
                errors.append("unexpected pilot arrays")
            features = np.asarray(archive["features"])
            positions = np.asarray(archive["positions"])
        if features.shape != (1, 8, 3072) or features.dtype != np.float32 or not np.isfinite(features).all():
            errors.append("invalid feature tensor")
        if positions.shape != (8, 5) or positions.dtype != np.float32 or not np.isfinite(positions).all():
            errors.append("invalid position tensor")
        if not np.all(positions[:, 2] == 0):
            errors.append("non-current temporal coordinate")
        if set(positions[:, 1].tolist()) != {-1.0, 1.0}:
            errors.append("both cameras are not represented")
        feature_hash = hashlib.sha256(np.ascontiguousarray(features).tobytes()).hexdigest()
        position_hash = hashlib.sha256(np.ascontiguousarray(positions).tobytes()).hexdigest()
        if feature_hash != report.get("feature_sha256") or position_hash != report.get("position_sha256"):
            errors.append("array content hash mismatch")
    except Exception as exc:
        errors.append(f"feature archive error: {exc}")
    result = {
        "status": "SIMPLEWAM_VISUAL_FEATURE_PILOT_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_FEATURE_PILOT_AUDIT_FAIL",
        "errors": errors,
        "pilot_report_sha256": sha(report_path),
        "pilot_features_sha256": sha(feature_path),
        "observation_sha256": report.get("observation_sha256"),
        "robot_actions_executed": 0,
        "critic_updates": 0,
    }
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2))
    if errors:
        raise RuntimeError("; ".join(errors))
    (args.output / result["status"]).touch()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
