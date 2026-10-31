"""Build the development-only setwise corpus without opening confirmation labels."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    code = args.root / "setwise_contrastive_qgf_v1"
    sys.path.insert(0, str(args.root / "progress_pairwise_qgf_v1"))
    from pairwise_corpus import state_features

    if not (code / "final_audit_v1/SETWISE_CONTRASTIVE_FINAL_AUDIT_PASS").exists():
        raise RuntimeError("Independent population audit is missing")
    if not (code / "final_v1/SETWISE_CONTRASTIVE_DATA_ADMIT").exists():
        raise RuntimeError("Population was not admitted")
    manifest_path = code / "registration_v1/MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    development = [row for row in manifest["entries"] if row["setwise_split"] == "development"]
    if len(development) != 12:
        raise RuntimeError("Development denominator changed")

    states, actions, targets, candidates, group_ids, groups = [], [], [], [], [], []
    for group_index, entry in enumerate(development):
        index = int(entry["setwise_index"])
        folder = code / "pilot_v1_retry1" if index == 0 else code / "remaining_v1" / f"entry_{index:02d}"
        report = json.loads((folder / "REPORT.json").read_text())
        if report["episode_id"] != entry["episode_id"] or report["physical_input_group"] != entry["physical_input_group"]:
            raise RuntimeError("Development identity changed")
        group = folder / entry["episode_id"]
        with np.load(group / "bank.npz", allow_pickle=False) as saved:
            bank = np.asarray(saved["candidates_executed_normalized"], dtype=np.float32)
            hashes = saved["hashes"].tolist()
        if bank.shape != (8, 32, 7) or hashes != report["candidate_hashes"]:
            raise RuntimeError("Candidate bank changed")
        state = state_features(group / "frozen_policy_input.npz", entry["task_description"], 700 - int(entry["boundary_model_step"]))
        branches = {int(row["candidate_index"]): row for row in report["branches"]}
        if set(branches) != set(range(8)):
            raise RuntimeError("Incomplete development branch labels")
        fold = int(entry["family_rank"])
        if fold not in (0, 1, 2):
            raise RuntimeError("Development fold is not prospectively balanced")
        groups.append({
            "episode_id": entry["episode_id"],
            "family": entry["family"],
            "physical_input_group": entry["physical_input_group"],
            "entry_index": index,
            "fold": fold,
            "report_sha256": sha(folder / "REPORT.json"),
        })
        for candidate in range(8):
            states.append(state)
            actions.append(bank[candidate, :16])
            targets.append(float(branches[candidate]["progress_at_32"]["value"]))
            candidates.append(candidate)
            group_ids.append(group_index)
    if len(groups) != 12 or len(states) != 96:
        raise RuntimeError("Development corpus denominator changed")
    fold_counts = {fold: sum(group["fold"] == fold for group in groups) for fold in range(3)}
    if fold_counts != {0: 4, 1: 4, 2: 4}:
        raise RuntimeError("Development folds are not family balanced")

    args.output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(
        args.output / "CORPUS.npz",
        state=np.stack(states).astype(np.float32),
        action=np.stack(actions).astype(np.float32),
        target=np.asarray(targets, dtype=np.float32),
        candidate_index=np.asarray(candidates, dtype=np.int64),
        group_index=np.asarray(group_ids, dtype=np.int64),
    )
    metadata = {
        "status": "SETWISE_DEVELOPMENT_CORPUS_COMPLETE",
        "groups": groups,
        "fold_counts": fold_counts,
        "rows": 96,
        "state_dimension": int(states[0].size),
        "action_shape": [16, 7],
        "primary_target": "horizon32 continuous progress",
        "confirmation_labels_read": False,
        "forbidden_inputs": ["success", "future state", "future execution length", "simulator predicate"],
        "manifest_sha256": sha(manifest_path),
        "final_report_sha256_without_reading_contents": sha(code / "final_v1/REPORT.json"),
        "final_audit_sha256": sha(code / "final_audit_v1/REPORT.json"),
    }
    (args.output / "METADATA.json").write_text(json.dumps(metadata, indent=2, sort_keys=True))
    report = dict(metadata, corpus_sha256=sha(args.output / "CORPUS.npz"), metadata_sha256=sha(args.output / "METADATA.json"))
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
