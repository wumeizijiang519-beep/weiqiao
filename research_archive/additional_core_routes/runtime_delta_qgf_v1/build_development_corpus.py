"""Build 24-group Runtime-Delta development corpus without confirmation reads."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def branches_by_candidate(report):
    rows = {int(row["candidate_index"]): row for row in report["branches"]}
    if set(rows) != set(range(8)):
        raise RuntimeError("Incomplete N8 report")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runtime = args.root / "runtime_anchored_qgf_v1"
    setwise = args.root / "setwise_contrastive_qgf_v1"
    if not (runtime / "final_audit_v1/RUNTIME_ANCHORED_FINAL_AUDIT_PASS").exists():
        raise RuntimeError("Runtime-Anchored audit missing")
    if not (setwise / "final_audit_v1/SETWISE_CONTRASTIVE_FINAL_AUDIT_PASS").exists():
        raise RuntimeError("Setwise population audit missing")
    if not (setwise / "development_corpus_audit_v1/SETWISE_DEVELOPMENT_CORPUS_AUDIT_PASS").exists():
        raise RuntimeError("Setwise development corpus audit missing")

    with np.load(runtime / "critic_corpus_v1/CORPUS.npz", allow_pickle=False) as saved:
        runtime_arrays = {key: saved[key].copy() for key in saved.files}
    runtime_meta = json.loads((runtime / "critic_corpus_v1/METADATA.json").read_text())
    runtime_final = json.loads((runtime / "final_v1/REPORT.json").read_text())
    runtime_reports = {row["episode_id"]: row for row in runtime_final["results"]}
    with np.load(setwise / "development_corpus_v1/CORPUS.npz", allow_pickle=False) as saved:
        setwise_arrays = {key: saved[key].copy() for key in saved.files}
    setwise_meta = json.loads((setwise / "development_corpus_v1/METADATA.json").read_text())
    manifest = json.loads((setwise / "registration_v1/MANIFEST.json").read_text())
    entries = {row["episode_id"]: row for row in manifest["entries"]}

    states, actions, scalar_targets, component_targets, candidate_indices, group_indices = [], [], [], [], [], []
    groups = []

    def append_source(source_name, arrays, metadata, report_lookup):
        offset = len(groups)
        for local_group, group in enumerate(metadata["groups"]):
            episode = group["episode_id"]
            report = report_lookup(episode, group)
            branches = branches_by_candidate(report)
            physical = group["physical_input_group"]
            groups.append({
                "episode_id": episode,
                "family": group["family"],
                "physical_input_group": physical,
                "source": source_name,
                "source_group_index": local_group,
                "report_sha256": group.get("report_sha256"),
            })
            members = np.flatnonzero(arrays["group_index"] == local_group)
            if len(members) != 8:
                raise RuntimeError("Source group is not N8")
            members = members[np.argsort(arrays["candidate_index"][members])]
            for candidate, row_index in enumerate(members):
                components = np.asarray(branches[candidate]["progress_at_32"]["components"], dtype=np.float32)
                if components.shape != (2,) or not np.isfinite(components).all():
                    raise RuntimeError("Invalid progress component target")
                scalar = float(branches[candidate]["progress_at_32"]["value"])
                if abs(float(components.mean()) - scalar) > 1e-6:
                    raise RuntimeError("Frozen progress aggregation changed")
                if abs(float(arrays["target"][row_index]) - scalar) > 1e-6:
                    raise RuntimeError("Source scalar target changed")
                states.append(arrays["state"][row_index])
                actions.append(arrays["action"][row_index])
                scalar_targets.append(scalar)
                component_targets.append(components)
                candidate_indices.append(candidate)
                group_indices.append(offset + local_group)

    append_source("runtime_anchored_v1", runtime_arrays, runtime_meta,
                  lambda episode, group: runtime_reports[episode])

    def setwise_report(episode, group):
        index = int(entries[episode]["setwise_index"])
        folder = setwise / "pilot_v1_retry1" if index == 0 else setwise / "remaining_v1" / f"entry_{index:02d}"
        report_path = folder / "REPORT.json"
        if group.get("report_sha256") and sha(report_path) != group["report_sha256"]:
            raise RuntimeError("Setwise development report changed")
        return json.loads(report_path.read_text())

    append_source("setwise_development_v1", setwise_arrays, setwise_meta, setwise_report)
    if len(groups) != 24 or len({row["physical_input_group"] for row in groups}) != 24:
        raise RuntimeError("Development physical groups are not 24 unique groups")
    by_family = defaultdict(list)
    for index, group in enumerate(groups):
        rank = hashlib.sha256((group["physical_input_group"] + "|runtime-delta-v1").encode()).hexdigest()
        by_family[group["family"]].append((rank, index))
    folds = {}
    for family, rows in by_family.items():
        for rank, (_, index) in enumerate(sorted(rows)):
            folds[index] = rank % 3
    fold_counts = {fold: sum(value == fold for value in folds.values()) for fold in range(3)}
    if min(fold_counts.values()) < 7:
        raise RuntimeError("Family-balanced folds are unexpectedly uneven")
    for index, group in enumerate(groups):
        group["fold"] = folds[index]

    args.output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(
        args.output / "CORPUS.npz",
        state=np.stack(states).astype(np.float32),
        action=np.stack(actions).astype(np.float32),
        target_components=np.stack(component_targets).astype(np.float32),
        target_scalar=np.asarray(scalar_targets, dtype=np.float32),
        candidate_index=np.asarray(candidate_indices, dtype=np.int64),
        group_index=np.asarray(group_indices, dtype=np.int64),
    )
    metadata = {
        "status": "RUNTIME_DELTA_DEVELOPMENT_CORPUS_COMPLETE",
        "groups": groups,
        "fold_counts": fold_counts,
        "rows": 192,
        "state_dimension": int(states[0].size),
        "action_shape": [16, 7],
        "component_dimension": 2,
        "component_aggregation": "arithmetic mean",
        "confirmation_labels_read": False,
        "forbidden_inputs": ["official success", "future state", "future execution length", "simulator predicate"],
        "source_receipts": {
            "runtime_corpus_sha256": sha(runtime / "critic_corpus_v1/CORPUS.npz"),
            "runtime_final_sha256": sha(runtime / "final_v1/REPORT.json"),
            "setwise_development_corpus_sha256": sha(setwise / "development_corpus_v1/CORPUS.npz"),
            "setwise_final_audit_sha256": sha(setwise / "final_audit_v1/REPORT.json"),
        },
    }
    (args.output / "METADATA.json").write_text(json.dumps(metadata, indent=2, sort_keys=True))
    report = dict(metadata, corpus_sha256=sha(args.output / "CORPUS.npz"), metadata_sha256=sha(args.output / "METADATA.json"))
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
