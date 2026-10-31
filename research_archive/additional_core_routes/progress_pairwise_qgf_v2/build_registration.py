"""Build the prospective 32-group V2 development/confirmation cohort."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np


V2_TAG = "progress-pairwise-qgf-v2:"


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--dataset-result", type=Path, required=True)
    parser.add_argument("--failure-critical-cohort", type=Path, required=True)
    parser.add_argument("--v1-manifest", type=Path, required=True)
    parser.add_argument("--v1-support-bases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str((args.root / "progress_pairwise_qgf_v1").resolve()))
    from build_registration import DATASET_SHA, inspect_episode

    if file_sha(args.dataset_result) != DATASET_SHA:
        raise RuntimeError("Frozen DATASET_RESULT changed")
    dataset = json.loads(args.dataset_result.read_text())
    if dataset.get("status") != "ADMIT_FOR_RL_QUALIFICATION" or dataset.get("episodes") != 288:
        raise RuntimeError("Frozen training dataset is not admitted")
    failure = json.loads(args.failure_critical_cohort.read_text())
    v1 = json.loads(args.v1_manifest.read_text())
    excluded = {row["physical_input_group"] for row in failure["entries"]}
    excluded.update(row["physical_input_group"] for row in v1["entries"])
    if len(excluded) != 32:
        raise RuntimeError("Prior prospective cohorts overlap or changed")

    by_group = {}
    inspected = 0
    for entry in sorted(dataset["entries"], key=lambda row: row["episode_id"]):
        record, _ = inspect_episode(entry, excluded)
        inspected += 1
        if record is None:
            continue
        record["selection_rank_sha256"] = hashlib.sha256(
            (V2_TAG + record["physical_input_group"]).encode()).hexdigest()
        by_group.setdefault(record["physical_input_group"], record)

    selected = []
    inventory = {}
    families = sorted({row["family"] for row in by_group.values()})
    if len(families) != 4:
        raise RuntimeError("Expected four frozen task families")
    for family in families:
        rows = sorted((row for row in by_group.values() if row["family"] == family),
                      key=lambda row: row["selection_rank_sha256"])
        if len(rows) < 8:
            raise RuntimeError("Fewer than eight new groups for " + family)
        for index, row in enumerate(rows[:8]):
            row["v2_split"] = "development" if index < 4 else "confirmation"
            row["family_rank"] = index
            selected.append(row)
        inventory[family] = {"eligible_groups": len(rows), "development": 4, "confirmation": 4}
    if len(selected) != 32 or len({row["physical_input_group"] for row in selected}) != 32:
        raise RuntimeError("V2 cohort is not 32 unique groups")
    if excluded.intersection(row["physical_input_group"] for row in selected):
        raise RuntimeError("V2 overlaps a prior prospective cohort")

    args.output.mkdir(parents=True, exist_ok=False)
    basis_path = args.output / "SUPPORT_BASES.npz"
    shutil.copyfile(args.v1_support_bases, basis_path)
    if file_sha(basis_path) != v1["support_bases_sha256"]:
        raise RuntimeError("Frozen V1 support basis changed")
    result = {
        "status": "PROGRESS_PAIRWISE_QGF_V2_PROSPECTIVE_REGISTERED",
        "dataset_result_sha256": DATASET_SHA,
        "failure_critical_cohort_sha256": file_sha(args.failure_critical_cohort),
        "v1_manifest_sha256": file_sha(args.v1_manifest),
        "v1_support_bases_sha256": file_sha(basis_path),
        "excluded_prior_groups": 32,
        "inspected_training_episodes": inspected,
        "eligible_physical_groups": len(by_group),
        "family_inventory": inventory,
        "support": v1["support"],
        "groups": 32,
        "development_groups": 16,
        "confirmation_groups": 16,
        "entries": selected,
        "selection_uses_v2_candidate_outcomes": False,
        "validation_or_formal_read": False,
        "replacement_after_execution_allowed": False,
    }
    manifest = args.output / "MANIFEST.json"
    manifest.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / "SHA256SUMS").write_text(
        f"{file_sha(manifest)}  MANIFEST.json\n{file_sha(basis_path)}  SUPPORT_BASES.npz\n")
    print(json.dumps({key: result[key] for key in
        ("status", "groups", "development_groups", "confirmation_groups",
         "eligible_physical_groups", "family_inventory")}, indent=2))


if __name__ == "__main__": main()
