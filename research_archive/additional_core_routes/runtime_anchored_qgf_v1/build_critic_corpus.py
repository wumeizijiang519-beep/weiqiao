"""Build deployment-visible Runtime-Anchored pairwise critic corpus."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "progress_pairwise_qgf_v1"))
from pairwise_corpus import deterministic_folds, state_features  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    code = Path(__file__).parent
    final_path = code / "final_v1" / "REPORT.json"
    audit_path = code / "final_audit_v1" / "REPORT.json"
    final = json.loads(final_path.read_text())
    audit = json.loads(audit_path.read_text())
    if final["status"] != "RUNTIME_ANCHORED_ACTION_VALUE_SIGNAL_ADMIT":
        raise RuntimeError("Population signal was not admitted")
    if audit["status"] != "RUNTIME_ANCHORED_FINAL_AUDIT_PASS":
        raise RuntimeError("Independent final audit missing")
    manifest = json.loads((code / "registration_v1_retry1" / "MANIFEST.json").read_text())
    entries = {row["episode_id"]: (i, row) for i, row in enumerate(manifest["entries"])}
    receipts = {row["entry_index"]: row["report_sha256"] for row in final["report_receipts"]}
    states, actions, targets, candidates, group_ids, groups = [], [], [], [], [], []
    for group_index, result in enumerate(final["results"]):
        episode_id = result["episode_id"]
        entry_index, entry = entries[episode_id]
        if entry_index == 0:
            folder = code / "pilot_v1_retry1"
        elif entry_index <= 10:
            folder = code / "remaining_v1" / f"entry_{entry_index:02d}"
        elif entry_index == 11:
            folder = code / "resume_entry11_v1_retry1"
        else:
            raise RuntimeError("Unexpected executed index")
        if sha(folder / "REPORT.json") != receipts[entry_index]:
            raise RuntimeError("Report receipt changed")
        group = folder / episode_id
        with np.load(group / "bank.npz", allow_pickle=False) as saved:
            bank = np.asarray(saved["candidates_executed_normalized"], dtype=np.float32)
            hashes = saved["hashes"].tolist()
        if bank.shape != (8, 32, 7) or hashes != result["candidate_hashes"]:
            raise RuntimeError("Candidate bank changed")
        state = state_features(
            group / "frozen_policy_input.npz",
            entry["task_description"],
            700 - int(entry["boundary_model_step"]),
        )
        branches = {int(row["candidate_index"]): row for row in result["branches"]}
        if set(branches) != set(range(8)):
            raise RuntimeError("Incomplete branch labels")
        groups.append({
            "episode_id": episode_id,
            "family": result["family"],
            "physical_input_group": result["physical_input_group"],
            "entry_index": entry_index,
        })
        for candidate in range(8):
            states.append(state)
            actions.append(bank[candidate, :16])
            targets.append(float(branches[candidate]["progress_at_32"]["value"]))
            candidates.append(candidate)
            group_ids.append(group_index)
    if len(groups) != 12 or len(states) != 96:
        raise RuntimeError("Scientific denominator changed")
    folds = deterministic_folds(groups, folds=3)
    if set(folds.values()) != {0, 1, 2}:
        raise RuntimeError("Invalid three-fold assignment")
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
        "status": "RUNTIME_ANCHORED_CRITIC_CORPUS_COMPLETE",
        "groups": groups,
        "fold_assignment": folds,
        "rows": 96,
        "state_dimension": int(states[0].size),
        "action_shape": [16, 7],
        "primary_target": "horizon32 continuous progress",
        "forbidden_inputs": ["success", "future state", "future execution length", "simulator predicate"],
        "final_report_sha256": sha(final_path),
        "final_audit_sha256": sha(audit_path),
    }
    (args.output / "METADATA.json").write_text(json.dumps(metadata, indent=2, sort_keys=True))
    report = dict(metadata, corpus_sha256=sha(args.output / "CORPUS.npz"),
                  metadata_sha256=sha(args.output / "METADATA.json"))
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
