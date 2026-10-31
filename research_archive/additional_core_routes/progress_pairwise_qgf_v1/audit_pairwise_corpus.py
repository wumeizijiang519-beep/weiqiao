"""Independent fail-closed audit of the pairwise critic corpus."""

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
    parser.add_argument("--final-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    meta = json.loads((args.corpus_dir / "METADATA.json").read_text())
    report = json.loads((args.corpus_dir / "REPORT.json").read_text())
    final = json.loads(args.final_report.read_text())
    errors = []
    if set(report) - {"corpus_sha256", "metadata_sha256"} != set(meta):
        errors.append("metadata/report inventory differs")
    if report.get("corpus_sha256") != sha(args.corpus_dir / "CORPUS.npz"):
        errors.append("corpus hash differs")
    if report.get("metadata_sha256") != sha(args.corpus_dir / "METADATA.json"):
        errors.append("metadata hash differs")
    with np.load(args.corpus_dir / "CORPUS.npz", allow_pickle=False) as saved:
        expected_arrays = {"state", "action", "target16", "target32", "candidate_index", "group_index"}
        if set(saved.files) != expected_arrays:
            errors.append("unexpected corpus arrays")
        arrays = {key: saved[key] for key in saved.files}
    if arrays["state"].shape != (112, 1674) or arrays["action"].shape != (112, 16, 7):
        errors.append("fitting shape differs")
    if not all(np.isfinite(value).all() for value in arrays.values()):
        errors.append("non-finite fitting array")
    if not np.array_equal(np.unique(arrays["group_index"], return_counts=True)[1], np.full(14, 8)):
        errors.append("group rows are not exactly N8")
    if not all(np.array_equal(
            arrays["state"][arrays["group_index"] == group],
            np.repeat(arrays["state"][arrays["group_index"] == group][:1], 8, axis=0))
            for group in range(14)):
        errors.append("candidate rows do not share the frozen group state")
    truth = {}
    for group in final["results"]:
        truth[group["episode_id"]] = {int(row["candidate_index"]):
            (row["progress_at_16"]["value"], row["progress_at_32"]["value"])
            for row in group["branches"]}
    for group_index, group in enumerate(meta["groups"]):
        rows = np.flatnonzero(arrays["group_index"] == group_index)
        for row in rows:
            candidate = int(arrays["candidate_index"][row])
            expected_target = truth[group["episode_id"]][candidate]
            if (float(arrays["target16"][row]) != np.float32(expected_target[0]).item()
                    or float(arrays["target32"][row]) != np.float32(expected_target[1]).item()):
                errors.append("target receipt differs")
    folds = list(meta["fold_assignment"].values())
    if set(folds) != {0, 1, 2, 3} or len(meta["fold_assignment"]) != 14:
        errors.append("invalid group-disjoint folds")
    result = {"status": "PAIRWISE_CRITIC_CORPUS_AUDIT_PASS" if not errors else "PAIRWISE_CRITIC_CORPUS_AUDIT_FAIL",
              "errors": errors, "rows": 112, "groups": 14,
              "corpus_sha256": sha(args.corpus_dir / "CORPUS.npz"),
              "metadata_sha256": sha(args.corpus_dir / "METADATA.json"),
              "forbidden_input_arrays_absent": not errors and set(arrays) == expected_arrays}
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    if errors: raise RuntimeError(errors)


if __name__ == "__main__": main()
