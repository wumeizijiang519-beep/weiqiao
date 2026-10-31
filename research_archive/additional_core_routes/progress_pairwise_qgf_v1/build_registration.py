"""Build the prospective cohort and family action-support basis."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


DATASET_SHA = "baa8340ecbe48ce0240e6e46056ed4e00309ba42e998657cda53ca7ec8666b87"
RANK_TAG = "progress-pairwise-qgf-v1:"


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def load_transition(folder, index, expected_sha):
    path = folder / f"transition_{index:04d}" / "transition.npz"
    if file_sha(path) != expected_sha:
        raise RuntimeError("Certified transition changed: " + str(path))
    with np.load(path, allow_pickle=False) as data:
        return {key: np.asarray(data[key]).copy() for key in data.files}


def boundary_score(previous, current):
    left = np.asarray(previous["executed_actions"], dtype=np.float64)
    right = np.asarray(current["executed_actions"], dtype=np.float64)
    if left.ndim != 2 or right.ndim != 2 or left.shape[1] != 7 or right.shape[1] != 7:
        raise RuntimeError("Invalid executed action shape")
    arm_change = float(np.linalg.norm(right[0, :6] - left[-1, :6]))
    grip_change = float(np.sign(right[0, 6]) != np.sign(left[-1, 6]))
    return arm_change + grip_change


def inspect_episode(entry, excluded_groups):
    if not entry.get("audit_pass") or not entry.get("success"):
        return None, []
    if entry["physical_input_group"] in excluded_groups:
        return None, []
    folder = Path(entry["episode_directory"])
    summary_path = folder / "summary.json"
    if file_sha(summary_path) != entry["summary_sha256"]:
        raise RuntimeError("Certified summary changed: " + entry["episode_id"])
    summary = json.loads(summary_path.read_text())
    transitions = summary["transitions"]
    event_indices = [i for i, row in enumerate(transitions) if float(row["reward_sum"]) > 0]
    if not event_indices:
        raise RuntimeError("Successful episode has no positive reward")
    event = event_indices[0]
    lengths = [int(row["length"]) for row in transitions]
    loaded = {}

    def get(index):
        if index not in loaded:
            loaded[index] = load_transition(folder, index, transitions[index]["transition_sha256"])
        return loaded[index]

    candidates = []
    for boundary in range(1, event + 1):
        distance = sum(lengths[boundary:event + 1])
        if 24 <= distance <= 64:
            candidates.append((boundary_score(get(boundary - 1), get(boundary)), boundary, distance))
    if not candidates:
        return None, []
    score, boundary, distance = sorted(candidates, key=lambda row: (-row[0], row[1]))[0]
    observation = folder / f"observation_{boundary:04d}.npz"
    if not observation.exists():
        raise RuntimeError("Missing boundary observation")
    receipts = []
    prefix_steps = 0
    for index in range(boundary):
        row = transitions[index]
        data = get(index)
        actual = int(data["actual_length"])
        prefix_steps += actual
        receipts.append({"index": index, "sha256": row["transition_sha256"], "actual_length": actual})
    record = {
        "episode_id": entry["episode_id"],
        "family": entry["family"],
        "category": entry["category"],
        "physical_input_group": entry["physical_input_group"],
        "episode_directory": str(folder),
        "summary_sha256": entry["summary_sha256"],
        "environment_seed": summary["environment_seed"],
        "initial_state_index": summary["initial_state_index"],
        "initial_state_path": summary["initial_state_path"],
        "initial_file_sha256": summary["initial_file_sha256"],
        "bddl_path": summary["bddl_path"],
        "bddl_sha256": summary["bddl_sha256"],
        "task_description": summary["task_description"],
        "task_id": summary["task_id"],
        "dummy_steps": summary["dummy_steps"],
        "boundary_replan": boundary,
        "boundary_model_step": prefix_steps,
        "steps_to_first_reward": distance,
        "first_reward_replan": event,
        "criticality_score": score,
        "boundary_observation_path": str(observation),
        "boundary_observation_sha256": file_sha(observation),
        "transition_receipts": receipts,
        "selection_rank_sha256": hashlib.sha256(
            (RANK_TAG + entry["physical_input_group"]).encode()).hexdigest(),
    }
    support_rows = []
    for index, row in enumerate(transitions):
        data = get(index)
        native = np.asarray(data["candidates_raw_normalized"], dtype=np.float32)
        if native.shape != (4, 32, 7) or not np.isfinite(native).all():
            raise RuntimeError("Invalid candidate bank")
        support_rows.extend((native[i, :, :6] - native[0, :, :6]).reshape(-1) for i in range(1, 4))
    return record, support_rows


def fit_support(rows):
    matrix = np.asarray(rows, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != 32 * 6 or len(matrix) < 4:
        raise RuntimeError("Insufficient support rows")
    norms = np.linalg.norm(matrix, axis=1)
    center = matrix.mean(axis=0)
    _, singular, vh = np.linalg.svd(matrix - center, full_matrices=False)
    basis = vh[:3].astype(np.float32).reshape(3, 32, 6)
    for vector in basis:
        pivot = np.flatnonzero(np.abs(vector.reshape(-1)) > 1e-12)
        if len(pivot) and vector.reshape(-1)[pivot[0]] < 0:
            vector *= -1
    return {
        "rows": int(len(matrix)),
        "median_delta_norm": float(np.quantile(norms, 0.5)),
        "p95_delta_norm": float(np.quantile(norms, 0.95)),
        "singular_values_top3": [float(x) for x in singular[:3]],
        "basis_sha256": array_sha(basis),
    }, basis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-result", type=Path, required=True)
    parser.add_argument("--excluded-cohort", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if file_sha(args.dataset_result) != DATASET_SHA:
        raise RuntimeError("Frozen DATASET_RESULT hash mismatch")
    dataset = json.loads(args.dataset_result.read_text())
    if dataset.get("status") != "ADMIT_FOR_RL_QUALIFICATION" or dataset.get("episodes") != 288:
        raise RuntimeError("Frozen dataset is not admitted")
    excluded = json.loads(args.excluded_cohort.read_text())
    excluded_groups = {row["physical_input_group"] for row in excluded["entries"]}
    if len(excluded_groups) != 16:
        raise RuntimeError("Expected 16 excluded physical groups")

    by_group = {}
    support_by_family = {}
    inspected = 0
    for entry in sorted(dataset["entries"], key=lambda row: row["episode_id"]):
        record, rows = inspect_episode(entry, excluded_groups)
        inspected += 1
        if record is None:
            continue
        by_group.setdefault(record["physical_input_group"], record)
        support_by_family.setdefault(record["family"], []).extend(rows)
    if len(support_by_family) != 4:
        raise RuntimeError("Expected four task families")

    selected = []
    inventory = {}
    bases = {}
    support = {}
    for family in sorted(support_by_family):
        records = sorted((row for row in by_group.values() if row["family"] == family),
                         key=lambda row: row["selection_rank_sha256"])
        if len(records) < 4:
            raise RuntimeError("Fewer than four new groups for " + family)
        chosen = records[:4]
        selected.extend(chosen)
        inventory[family] = {"eligible_groups": len(records), "selected_groups": 4}
        support[family], bases[family] = fit_support(support_by_family[family])
    if len(selected) != 16 or len({row["physical_input_group"] for row in selected}) != 16:
        raise RuntimeError("Prospective cohort is not 16 unique groups")
    if excluded_groups.intersection(row["physical_input_group"] for row in selected):
        raise RuntimeError("New cohort overlaps the frozen prior cohort")

    args.output.mkdir(parents=True, exist_ok=False)
    basis_path = args.output / "SUPPORT_BASES.npz"
    np.savez_compressed(basis_path, **{family: bases[family] for family in sorted(bases)})
    result = {
        "status": "PROGRESS_PAIRWISE_QGF_V1_PROPOSED_NOT_GPU_AUTHORIZED",
        "dataset_result_sha256": DATASET_SHA,
        "excluded_cohort_sha256": file_sha(args.excluded_cohort),
        "excluded_groups": 16,
        "inspected_training_episodes": inspected,
        "eligible_physical_groups": len(by_group),
        "family_inventory": inventory,
        "support": support,
        "support_bases_sha256": file_sha(basis_path),
        "groups": 16,
        "entries": selected,
        "selection_uses_new_candidate_outcomes": False,
        "validation_or_formal_read": False,
        "replacement_after_execution_allowed": False,
    }
    manifest = args.output / "MANIFEST.json"
    manifest.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / "SHA256SUMS").write_text(
        f"{file_sha(manifest)}  MANIFEST.json\n{file_sha(basis_path)}  SUPPORT_BASES.npz\n")
    print(json.dumps({"status": result["status"], "groups": 16,
                      "eligible_physical_groups": len(by_group),
                      "family_inventory": inventory, "support": support}, indent=2))


if __name__ == "__main__":
    main()
