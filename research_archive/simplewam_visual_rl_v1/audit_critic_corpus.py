"""Independent source-level audit for the visual RL critic corpus."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.corpus / "REPORT.json").read_text())
    dataset = json.loads(args.dataset.read_text())
    entries = {row["episode_id"]: row for row in dataset["entries"]}
    errors = []
    corpus_path = args.corpus / "CORPUS.npz"
    if report.get("corpus_sha256") != sha256(corpus_path):
        errors.append("corpus hash mismatch")
    with np.load(corpus_path, allow_pickle=False) as archive:
        values = {key: archive[key] for key in archive.files}
    rows = len(values["token"])
    expected_shapes = {
        "token": (rows, 2048), "next_token": (rows, 2048),
        "proprio": (rows, 9), "next_proprio": (rows, 9),
        "action_prefix": (rows, 10, 7), "rewards": (rows, 10),
    }
    for key, shape in expected_shapes.items():
        if values.get(key, np.empty(0)).shape != shape:
            errors.append(f"{key} shape mismatch")
    for key in ("token", "next_token", "proprio", "next_proprio", "action_prefix", "rewards"):
        if key in values and not np.isfinite(values[key]).all():
            errors.append(f"{key} contains nonfinite values")
    group_fold = {}
    source_rows = 0
    for index in range(rows):
        episode_id = str(values["episode"][index])
        transition_index = int(values["transition"][index])
        entry = entries.get(episode_id)
        if entry is None:
            errors.append(f"unknown episode {episode_id}")
            continue
        group = str(values["group"][index])
        fold = int(values["fold"][index])
        if group != entry["physical_input_group"] or fold != int(entry["group_oof_fold"]):
            errors.append(f"group/fold mismatch at row {index}")
        if group in group_fold and group_fold[group] != fold:
            errors.append(f"physical group crosses folds: {group}")
        group_fold[group] = fold
        summary = json.loads((Path(entry["episode_directory"]) / "summary.json").read_text())
        receipt = summary["transitions"][transition_index]
        path = Path(entry["episode_directory"]) / receipt["path"] / "transition.npz"
        with np.load(path, allow_pickle=False) as transition:
            selected = int(transition["selected_index"])
            action = np.asarray(transition["candidates_raw_normalized"][selected, :10], dtype=np.float32)
            realized = int(transition["actual_length"])
            rewards = np.zeros(10, dtype=np.float32)
            rewards[:realized] = transition["rewards"][:realized]
            if not np.array_equal(action, values["action_prefix"][index]):
                errors.append(f"action receipt mismatch at row {index}")
            if not np.array_equal(rewards, values["rewards"][index]):
                errors.append(f"reward receipt mismatch at row {index}")
            if realized != int(values["realized_length"][index]):
                errors.append(f"realized length mismatch at row {index}")
            if bool(transition["terminal"]) != bool(values["terminal"][index]):
                errors.append(f"terminal mismatch at row {index}")
        source_rows += 1
        if len(errors) > 20:
            break
    audit = {
        "status": "SIMPLEWAM_VISUAL_RL_CRITIC_CORPUS_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_RL_CRITIC_CORPUS_AUDIT_FAILED",
        "errors": errors,
        "rows": rows,
        "source_rows_checked": source_rows,
        "episodes": len(set(values["episode"].tolist())),
        "physical_groups": len(group_fold),
        "folds": sorted(set(group_fold.values())),
        "planned_prefix_length": 10,
        "action_dim": 7,
        "realized_length_in_q_input": False,
        "corpus_sha256": sha256(corpus_path),
        "dataset_sha256": sha256(args.dataset),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(audit, indent=2))
    (args.output / audit["status"]).touch()
    print(json.dumps(audit, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
