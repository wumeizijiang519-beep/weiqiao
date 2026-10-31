"""Strongly regularized linear OOF worker on fixed physical action summaries."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import traceback

import numpy as np


SEEDS = (202642301, 202642302, 202642303)
UPDATES = 3000
TIE_EPS = 1e-6


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def action_summary(action):
    return np.concatenate((action.mean(1), action.std(1), action[:, 0], action[:, -1], action.sum(1)), axis=1).astype(np.float32)


def build_pairs(group_index, target, groups):
    left, right, label, pair_group = [], [], [], []
    for group in groups:
        members = np.flatnonzero(group_index == group)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                delta = float(target[members[i]] - target[members[j]])
                if abs(delta) <= TIE_EPS:
                    continue
                left.append(members[i]); right.append(members[j]); label.append(float(delta > 0)); pair_group.append(group)
    return tuple(np.asarray(value) for value in (left, right, label, pair_group))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    reg = json.loads(args.registration.read_text())
    if reg["seed"] not in SEEDS or reg["held_fold"] not in (0, 1, 2) or reg["updates"] != UPDATES:
        raise RuntimeError("Training contract changed")
    if sha(__file__) != reg["source_sha256"]:
        raise RuntimeError("Source changed")
    run = Path(reg["run_directory"]); run.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        import torch
        random.seed(reg["seed"]); np.random.seed(reg["seed"]); torch.manual_seed(reg["seed"])
        torch.cuda.manual_seed_all(reg["seed"]); torch.use_deterministic_algorithms(True)
        with np.load(reg["corpus"], allow_pickle=False) as saved:
            corpus = {key: saved[key].copy() for key in saved.files}
        meta = json.loads(Path(reg["metadata"]).read_text())
        if sha(reg["corpus"]) != reg["corpus_sha256"] or sha(reg["metadata"]) != reg["metadata_sha256"]:
            raise RuntimeError("Corpus changed")
        if meta.get("confirmation_labels_read") is not False:
            raise RuntimeError("Confirmation seal violated")
        fold = np.asarray([int(group["fold"]) for group in meta["groups"]])
        train_groups = np.flatnonzero(fold != reg["held_fold"]); held_groups = np.flatnonzero(fold == reg["held_fold"])
        train_rows = np.flatnonzero(np.isin(corpus["group_index"], train_groups))
        group_state = np.stack([corpus["state"][np.flatnonzero(corpus["group_index"] == group)[0]] for group in range(24)])
        state_mean = group_state[train_groups].mean(0)
        centered = group_state[train_groups] - state_mean
        _, _, vh = np.linalg.svd(centered, full_matrices=False)
        basis = vh[:8].astype(np.float32)
        state_pc_group = ((group_state - state_mean) @ basis.T).astype(np.float32)
        pc_mean = state_pc_group[train_groups].mean(0); pc_scale = np.maximum(state_pc_group[train_groups].std(0), 1e-5)
        state_pc_group = ((state_pc_group - pc_mean) / pc_scale).astype(np.float32)
        summary = action_summary(corpus["action"])
        summary_mean = summary[train_rows].mean(0); summary_scale = np.maximum(summary[train_rows].std(0), 1e-5)
        summary = ((summary - summary_mean) / summary_scale).astype(np.float32)
        state_pc = state_pc_group[corpus["group_index"]]
        proposed = np.concatenate((summary, (summary[:, :, None] * state_pc[:, None, :]).reshape(len(summary), -1)), axis=1)
        generator = np.random.default_rng(reg["seed"] + reg["held_fold"] * 1009)
        permutation = np.arange(len(summary))
        for group in range(24):
            members = np.flatnonzero(corpus["group_index"] == group)
            permutation[members] = generator.permutation(members)
        perm_summary = summary[permutation]
        perm_proposed = np.concatenate((perm_summary, (perm_summary[:, :, None] * state_pc[:, None, :]).reshape(len(summary), -1)), axis=1)
        train_pairs = build_pairs(corpus["group_index"], corpus["target_scalar"], train_groups)
        held_pairs = build_pairs(corpus["group_index"], corpus["target_scalar"], held_groups)
        device = "cuda"
        feature_np = {"proposed": proposed, "action_only": summary, "permutation": perm_proposed}
        features = {name: torch.as_tensor(value, device=device) for name, value in feature_np.items()}
        models = {name: torch.nn.Linear(value.shape[1], 1, bias=False).cuda() for name, value in features.items()}
        optimizers = {name: torch.optim.AdamW(model.parameters(), lr=1e-2, weight_decay=1e-2) for name, model in models.items()}
        for update in range(1, UPDATES + 1):
            if time.monotonic() - started > reg["hard_gpu_seconds"]:
                raise RuntimeError("Worker time exhausted")
            picked = generator.integers(0, len(train_pairs[0]), size=128)
            left = torch.as_tensor(train_pairs[0][picked], device=device); right = torch.as_tensor(train_pairs[1][picked], device=device)
            target = torch.as_tensor(train_pairs[2][picked], dtype=torch.float32, device=device)
            for name, model in models.items():
                logits = model(features[name][left]).squeeze(-1) - model(features[name][right]).squeeze(-1)
                loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, target)
                optimizers[name].zero_grad(set_to_none=True); loss.backward(); optimizers[name].step()
            if update % 500 == 0: print("fixed_update", update, flush=True)
        left = torch.as_tensor(held_pairs[0], device=device); right = torch.as_tensor(held_pairs[1], device=device)
        with torch.no_grad():
            predictions = {name: (model(features[name][left]).squeeze(-1) - model(features[name][right]).squeeze(-1)).cpu().numpy() for name, model in models.items()}
        predictions["state_only"] = np.zeros(len(held_pairs[0]), dtype=np.float32)
        np.savez_compressed(run / "HELD_PREDICTIONS.npz", target=held_pairs[2].astype(np.float32),
                            group_index=held_pairs[3].astype(np.int64), left_index=held_pairs[0].astype(np.int64),
                            right_index=held_pairs[1].astype(np.int64), **{k: v.astype(np.float32) for k, v in predictions.items()})
        np.savez_compressed(run / "NORMALIZER.npz", state_mean=state_mean, state_basis=basis, pc_mean=pc_mean,
                            pc_scale=pc_scale, summary_mean=summary_mean, summary_scale=summary_scale)
        torch.save({name: model.state_dict() for name, model in models.items()}, run / "FINAL_3000.pt")
        report = {"status": "REGULARIZED_LINEAR_WORKER_COMPLETE", "seed": reg["seed"], "held_fold": reg["held_fold"],
                  "updates": UPDATES, "held_pairs": int(len(held_pairs[0])), "held_groups": held_groups.tolist(),
                  "wall_seconds": time.monotonic() - started, "checkpoint_sha256": sha(run / "FINAL_3000.pt"),
                  "confirmation_labels_read": False}
        (run / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True)); (run / "WORKER_COMPLETE").touch()
    except BaseException:
        (run / "FAILED.txt").write_text(traceback.format_exc()); raise


if __name__ == "__main__": main()
