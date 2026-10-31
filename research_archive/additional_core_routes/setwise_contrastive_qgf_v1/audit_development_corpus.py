"""Independent fail-closed audit of the development-only corpus."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    meta = json.loads((args.corpus_dir / "METADATA.json").read_text())
    report = json.loads((args.corpus_dir / "REPORT.json").read_text())
    errors = []
    if report.get("corpus_sha256") != sha(args.corpus_dir / "CORPUS.npz"):
        errors.append("corpus hash")
    if report.get("metadata_sha256") != sha(args.corpus_dir / "METADATA.json"):
        errors.append("metadata hash")
    if meta.get("confirmation_labels_read") is not False:
        errors.append("confirmation seal")
    with np.load(args.corpus_dir / "CORPUS.npz", allow_pickle=False) as saved:
        expected = {"state", "action", "target", "candidate_index", "group_index"}
        if set(saved.files) != expected:
            errors.append("array inventory")
        arrays = {key: saved[key] for key in saved.files}
    if arrays["state"].shape != (96, 1674) or arrays["action"].shape != (96, 16, 7):
        errors.append("shape")
    if not all(np.isfinite(value).all() for value in arrays.values()):
        errors.append("nonfinite")
    unique, counts = np.unique(arrays["group_index"], return_counts=True)
    if not np.array_equal(unique, np.arange(12)) or not np.array_equal(counts, np.full(12, 8)):
        errors.append("group denominator")
    if meta.get("fold_counts") != {"0": 4, "1": 4, "2": 4}:
        errors.append("balanced folds")
    result = {
        "status": "SETWISE_DEVELOPMENT_CORPUS_AUDIT_PASS" if not errors else "SETWISE_DEVELOPMENT_CORPUS_AUDIT_FAIL",
        "errors": errors,
        "rows": 96,
        "groups": 12,
        "confirmation_labels_read": False,
        "forbidden_input_arrays_absent": not errors and set(arrays) == expected,
        "corpus_sha256": sha(args.corpus_dir / "CORPUS.npz"),
        "metadata_sha256": sha(args.corpus_dir / "METADATA.json"),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result["status"]).touch()
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
