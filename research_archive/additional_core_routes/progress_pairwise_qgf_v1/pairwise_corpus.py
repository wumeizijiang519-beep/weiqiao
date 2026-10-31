"""Build the immutable deployment-visible corpus for pairwise critic training."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


TIE_TOLERANCE = 1e-6
IMAGE_GRID = 16
TEXT_DIMENSION = 128


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pooled_image(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value)
    if value.shape != (256, 256, 3) or value.dtype != np.uint8:
        raise ValueError(f"Unexpected policy image contract: {value.shape}/{value.dtype}")
    block = 256 // IMAGE_GRID
    pooled = value.reshape(IMAGE_GRID, block, IMAGE_GRID, block, 3).mean((1, 3)) / 255.0
    return pooled.astype(np.float32).reshape(-1)


def _instruction_features(text: str) -> np.ndarray:
    result = np.zeros(TEXT_DIMENSION, dtype=np.float32)
    tokens = [token for token in text.lower().replace("_", " ").split() if token]
    for token in tokens:
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "little") % TEXT_DIMENSION
        result[index] += 1.0 if digest[4] & 1 else -1.0
    norm = float(np.linalg.norm(result))
    return result / norm if norm else result


def state_features(policy_input: Path, task_description: str, remaining_steps: int) -> np.ndarray:
    with np.load(policy_input, allow_pickle=False) as data:
        expected = {
            "agentview_image", "robot0_eye_in_hand_image", "robot0_eef_pos",
            "robot0_eef_quat", "robot0_gripper_qpos",
        }
        if set(data.files) != expected:
            raise ValueError("Frozen policy input inventory changed")
        proprio = np.concatenate([
            np.asarray(data["robot0_eef_pos"], dtype=np.float32),
            np.asarray(data["robot0_eef_quat"], dtype=np.float32),
            np.asarray(data["robot0_gripper_qpos"], dtype=np.float32),
        ])
        if proprio.shape != (9,) or not np.isfinite(proprio).all():
            raise ValueError("Invalid deployment-visible proprioception")
        result = np.concatenate([
            _pooled_image(data["agentview_image"]),
            _pooled_image(data["robot0_eye_in_hand_image"]),
            proprio,
            _instruction_features(task_description),
            np.asarray([remaining_steps / 700.0], dtype=np.float32),
        ]).astype(np.float32)
    if not np.isfinite(result).all():
        raise ValueError("Non-finite state feature")
    return result


def deterministic_folds(groups: list[dict], folds: int = 4) -> dict[str, int]:
    by_family: dict[str, list[dict]] = {}
    for row in groups:
        by_family.setdefault(row["family"], []).append(row)
    assignment = {}
    for family, rows in sorted(by_family.items()):
        ranked = sorted(rows, key=lambda row: hashlib.sha256(
            (row["episode_id"] + "|pairwise-critic-v1").encode()).hexdigest())
        for index, row in enumerate(ranked):
            assignment[row["episode_id"]] = index % folds
    if set(assignment) != {row["episode_id"] for row in groups}:
        raise RuntimeError("Incomplete fold assignment")
    return assignment


def _group_directory(root: Path, entry_index: int, episode_id: str) -> Path:
    base = root / "pilot_v1" if entry_index == 0 else root / "remaining_v1" / f"entry_{entry_index:02d}"
    path = base / episode_id
    if not path.is_dir():
        raise FileNotFoundError(path)
    return path


def build(root: Path, output: Path) -> dict:
    final_path = root / "final_v1" / "REPORT.json"
    audit_path = root / "final_audit_v1" / "REPORT.json"
    final = json.loads(final_path.read_text())
    audit = json.loads(audit_path.read_text())
    if (final["status"] != "PROGRESS_PAIRWISE_ACTION_VALUE_SIGNAL_ADMIT"
            or audit["status"] != "PROGRESS_PAIRWISE_FINAL_AUDIT_PASS"
            or audit["final_report_sha256"] != sha256(final_path)):
        raise RuntimeError("Frozen population qualification is missing")
    manifest = json.loads((root / "registration_v1" / "MANIFEST.json").read_text())
    entries = {row["episode_id"]: (index, row) for index, row in enumerate(manifest["entries"])}
    receipt = {row["entry_index"]: row["report_sha256"] for row in final["report_receipts"]}
    states, actions, targets16, targets32, candidate_ids, group_ids = [], [], [], [], [], []
    groups = []
    for group_index, result in enumerate(final["results"]):
        episode_id = result["episode_id"]
        entry_index, entry = entries[episode_id]
        group_dir = _group_directory(root, entry_index, episode_id)
        report_path = group_dir.parent / "REPORT.json"
        if sha256(report_path) != receipt[entry_index]:
            raise RuntimeError(f"Group report receipt changed: {episode_id}")
        with np.load(group_dir / "bank.npz", allow_pickle=False) as bank:
            candidate = np.asarray(bank["candidates_executed_normalized"], dtype=np.float32)
            hashes = [str(value) for value in bank["hashes"]]
        if candidate.shape != (8, 32, 7) or hashes != result["candidate_hashes"]:
            raise RuntimeError(f"Candidate bank changed: {episode_id}")
        state = state_features(group_dir / "frozen_policy_input.npz", entry["task_description"],
                               700 - int(entry["boundary_model_step"]))
        branches = {int(row["candidate_index"]): row for row in result["branches"]}
        if set(branches) != set(range(8)):
            raise RuntimeError(f"Incomplete branch labels: {episode_id}")
        groups.append({
            "episode_id": episode_id,
            "family": result["family"],
            "physical_input_group": result["physical_input_group"],
            "entry_index": entry_index,
        })
        for candidate_index in range(8):
            branch = branches[candidate_index]
            states.append(state)
            actions.append(candidate[candidate_index, :16])
            targets16.append(float(branch["progress_at_16"]["value"]))
            targets32.append(float(branch["progress_at_32"]["value"]))
            candidate_ids.append(candidate_index)
            group_ids.append(group_index)
    if len(groups) != 14 or len(states) != 112:
        raise RuntimeError("Scientific denominator changed")
    folds = deterministic_folds(groups)
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output / "CORPUS.npz",
        state=np.stack(states).astype(np.float32),
        action=np.stack(actions).astype(np.float32),
        target16=np.asarray(targets16, dtype=np.float32),
        target32=np.asarray(targets32, dtype=np.float32),
        candidate_index=np.asarray(candidate_ids, dtype=np.int64),
        group_index=np.asarray(group_ids, dtype=np.int64))
    metadata = {
        "status": "PROGRESS_PAIRWISE_CRITIC_CORPUS_COMPLETE",
        "final_report_sha256": sha256(final_path),
        "final_audit_sha256": sha256(audit_path),
        "groups": groups,
        "fold_assignment": folds,
        "rows": 112,
        "state_dimension": int(states[0].size),
        "action_shape": [16, 7],
        "primary_target": "horizon32 continuous progress",
        "secondary_target": "horizon16 continuous progress",
        "tie_tolerance": TIE_TOLERANCE,
        "input_contract": "two 16x16 pooled policy cameras + proprio9 + hashed instruction128 + known remaining horizon",
        "forbidden_inputs": ["success", "future state", "future execution length", "progress label", "simulator predicate"],
    }
    (output / "METADATA.json").write_text(json.dumps(metadata, indent=2, sort_keys=True))
    report = dict(metadata, corpus_sha256=sha256(output / "CORPUS.npz"),
                  metadata_sha256=sha256(output / "METADATA.json"))
    (output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (output / "CORPUS_COMPLETE").touch()
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.output), indent=2))
