"""Fixed direct-pairwise development OOF worker with matched controls."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import traceback

import numpy as np


SEEDS = (202642301, 202642302, 202642303)
MODELS = ("proposed", "state_only", "permutation", "action_only")
UPDATES = 3000
TIE_EPS = 1e-6


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_pairs(group_index, target_scalar, groups):
    left, right, label, pair_group = [], [], [], []
    for group in groups:
        members = np.flatnonzero(group_index == group)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                delta = float(target_scalar[members[i]] - target_scalar[members[j]])
                if abs(delta) <= TIE_EPS:
                    continue
                left.append(members[i]); right.append(members[j])
                label.append(float(delta > 0)); pair_group.append(group)
    return tuple(np.asarray(value) for value in (left, right, label, pair_group))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    reg = json.loads(args.registration.read_text())
    if reg["seed"] not in SEEDS or reg["held_fold"] not in (0, 1, 2) or reg["updates"] != UPDATES:
        raise RuntimeError("Training contract changed")
    code = Path(__file__).parent
    for name, digest in reg["source_sha256"].items():
        if sha(code / name) != digest:
            raise RuntimeError("Source changed: " + name)
    audit = json.loads(Path(reg["corpus_audit"]).read_text())
    if sha(reg["corpus_audit"]) != reg["corpus_audit_sha256"] or audit["status"] != "RUNTIME_DELTA_DEVELOPMENT_CORPUS_AUDIT_PASS":
        raise RuntimeError("Development corpus audit missing")
    run = Path(reg["run_directory"])
    run.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        import torch
        from pairwise_model import ActionOnlyScorer, ConditionalScorer, StateOnlyScorer

        random.seed(reg["seed"]); np.random.seed(reg["seed"]); torch.manual_seed(reg["seed"])
        torch.cuda.manual_seed_all(reg["seed"]); torch.backends.cuda.matmul.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        with np.load(reg["corpus"], allow_pickle=False) as saved:
            corpus = {key: saved[key].copy() for key in saved.files}
        meta = json.loads(Path(reg["metadata"]).read_text())
        if sha(reg["corpus"]) != reg["corpus_sha256"] or sha(reg["metadata"]) != reg["metadata_sha256"]:
            raise RuntimeError("Corpus changed")
        if meta.get("confirmation_labels_read") is not False:
            raise RuntimeError("Confirmation seal violated")
        fold = np.asarray([int(group["fold"]) for group in meta["groups"]], dtype=np.int64)
        train_groups = np.flatnonzero(fold != reg["held_fold"])
        held_groups = np.flatnonzero(fold == reg["held_fold"])
        train_rows = np.flatnonzero(np.isin(corpus["group_index"], train_groups))
        state_mean = corpus["state"][train_rows].mean(0).astype(np.float32)
        state_scale = np.maximum(corpus["state"][train_rows].std(0), 1e-5).astype(np.float32)
        state = ((corpus["state"] - state_mean) / state_scale).astype(np.float32)
        train_pairs = build_pairs(corpus["group_index"], corpus["target_scalar"], train_groups)
        held_pairs = build_pairs(corpus["group_index"], corpus["target_scalar"], held_groups)
        if len(train_pairs[0]) == 0 or len(held_pairs[0]) == 0:
            raise RuntimeError("Empty non-tie pair split")
        generator = np.random.default_rng(reg["seed"] + reg["held_fold"] * 1009)
        permutation = np.arange(len(corpus["action"]), dtype=np.int64)
        for group in range(24):
            members = np.flatnonzero(corpus["group_index"] == group)
            permutation[members] = generator.permutation(members)
        device = "cuda"
        state_t = torch.as_tensor(state, device=device)
        action_t = torch.as_tensor(corpus["action"], device=device)
        perm_action_t = action_t[torch.as_tensor(permutation, device=device)]
        models = {
            "proposed": ConditionalScorer(state.shape[1]).cuda(),
            "permutation": ConditionalScorer(state.shape[1]).cuda(),
            "state_only": StateOnlyScorer(state.shape[1]).cuda(),
            "action_only": ActionOnlyScorer(state.shape[1]).cuda(),
        }
        optimizers = {name: torch.optim.Adam(model.parameters(), lr=3e-4) for name, model in models.items()}
        for update in range(1, UPDATES + 1):
            if time.monotonic() - started > reg["hard_gpu_seconds"]:
                raise RuntimeError("Worker time exhausted")
            picked = generator.integers(0, len(train_pairs[0]), size=128)
            left = torch.as_tensor(train_pairs[0][picked], device=device)
            right = torch.as_tensor(train_pairs[1][picked], device=device)
            target = torch.as_tensor(train_pairs[2][picked], dtype=torch.float32, device=device)
            for name, model in models.items():
                supplied = perm_action_t if name == "permutation" else action_t
                logits = model(state_t[left], supplied[left]) - model(state_t[right], supplied[right])
                loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, target)
                optimizers[name].zero_grad(set_to_none=True); loss.backward(); optimizers[name].step()
            if update % 500 == 0:
                print("fixed_update", update, flush=True)
        held_left = torch.as_tensor(held_pairs[0], device=device)
        held_right = torch.as_tensor(held_pairs[1], device=device)
        predictions = {}
        with torch.no_grad():
            for name, model in models.items():
                supplied = perm_action_t if name == "permutation" else action_t
                predictions[name] = (
                    model(state_t[held_left], supplied[held_left])
                    - model(state_t[held_right], supplied[held_right])
                ).cpu().numpy()
        np.savez_compressed(
            run / "HELD_PREDICTIONS.npz",
            target=held_pairs[2].astype(np.float32),
            group_index=held_pairs[3].astype(np.int64),
            left_index=held_pairs[0].astype(np.int64),
            right_index=held_pairs[1].astype(np.int64),
            **{name: value.astype(np.float32) for name, value in predictions.items()},
        )
        np.savez_compressed(run / "NORMALIZER.npz", state_mean=state_mean, state_scale=state_scale)
        torch.save({name: model.state_dict() for name, model in models.items()}, run / "FINAL_3000.pt")
        report = {
            "status": "DIRECT_PAIRWISE_DEVELOPMENT_WORKER_COMPLETE",
            "seed": reg["seed"], "held_fold": reg["held_fold"], "updates": UPDATES,
            "held_pairs": int(len(held_pairs[0])), "held_groups": held_groups.tolist(),
            "wall_seconds": time.monotonic() - started,
            "checkpoint_sha256": sha(run / "FINAL_3000.pt"),
            "confirmation_labels_read": False,
        }
        (run / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
        (run / "WORKER_COMPLETE").touch()
    except BaseException:
        (run / "FAILED.txt").write_text(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
