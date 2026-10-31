"""Build the prospective 24-group setwise cohort."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


TAG = "setwise-contrastive-qgf-v1:"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--dataset-result", type=Path, required=True)
    parser.add_argument("--failure-critical", type=Path, required=True)
    parser.add_argument("--v1-manifest", type=Path, required=True)
    parser.add_argument("--v2-manifest", type=Path, required=True)
    parser.add_argument("--support-bases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str((args.root / "progress_pairwise_qgf_v1").resolve()))
    from build_registration import DATASET_SHA, inspect_episode

    if sha(args.dataset_result) != DATASET_SHA:
        raise RuntimeError("Dataset receipt changed")
    dataset = json.loads(args.dataset_result.read_text())
    failure = json.loads(args.failure_critical.read_text())
    v1 = json.loads(args.v1_manifest.read_text())
    v2 = json.loads(args.v2_manifest.read_text())
    excluded = {row["physical_input_group"] for row in failure["entries"]}
    excluded.update(row["physical_input_group"] for row in v1["entries"])
    excluded.update(row["physical_input_group"] for row in v2["entries"])
    if len(excluded) != 64:
        raise RuntimeError("Prior cohorts overlap or changed")
    by_group = {}
    for source in sorted(dataset["entries"], key=lambda row: row["episode_id"]):
        record, _ = inspect_episode(source, excluded)
        if record is None:
            continue
        record["selection_rank_sha256"] = hashlib.sha256(
            (TAG + record["physical_input_group"]).encode()
        ).hexdigest()
        by_group.setdefault(record["physical_input_group"], record)
    selected = []
    inventory = {}
    families = sorted({row["family"] for row in by_group.values()})
    if len(families) != 4:
        raise RuntimeError("Expected four task families")
    for family in families:
        rows = sorted(
            (row for row in by_group.values() if row["family"] == family),
            key=lambda row: row["selection_rank_sha256"],
        )
        if len(rows) < 6:
            raise RuntimeError("Fewer than six eligible groups for " + family)
        for rank, row in enumerate(rows[:6]):
            row["setwise_split"] = "development" if rank < 3 else "confirmation"
            row["family_rank"] = rank
            row["setwise_index"] = len(selected)
            selected.append(row)
        inventory[family] = {"eligible": len(rows), "development": 3, "confirmation": 3}
    if len(selected) != 24 or len({row["physical_input_group"] for row in selected}) != 24:
        raise RuntimeError("Invalid setwise cohort")
    args.output.mkdir(parents=True, exist_ok=False)
    basis = args.output / "SUPPORT_BASES.npz"
    shutil.copyfile(args.support_bases, basis)
    manifest = {
        "status": "RUNTIME_ANCHORED_QGF_V1_REGISTERED",
        "branch_contract": "SETWISE_CONTRASTIVE_QGF_V1",
        "groups": 24,
        "pilot_index": 0,
        "entries": selected,
        "support": v1["support"],
        "support_bases_sha256": sha(basis),
        "dataset_result_sha256": DATASET_SHA,
        "excluded_prior_groups": 64,
        "family_inventory": inventory,
        "selection_reads_candidate_outcomes": False,
        "validation_or_formal_read": False,
        "replacement_allowed": False,
    }
    path = args.output / "MANIFEST.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    (args.output / "SHA256SUMS").write_text(
        f"{sha(path)}  MANIFEST.json\n{sha(basis)}  SUPPORT_BASES.npz\n"
    )


if __name__ == "__main__":
    main()
