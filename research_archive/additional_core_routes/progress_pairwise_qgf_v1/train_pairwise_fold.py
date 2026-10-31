"""Fixed-update, matched-control Progress-Pairwise critic worker."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import traceback

import numpy as np

from pairwise_corpus import TIE_TOLERANCE, sha256


SEEDS = (202641601, 202641602, 202641603)
MODELS = ("action_aware", "state_only", "permutation")
SOURCES = ("train_pairwise_fold.py", "pairwise_model.py", "pairwise_corpus.py")


def pair_indices(group_index, target):
    rows = []
    for group in np.unique(group_index):
        members = np.flatnonzero(group_index == group)
        for i, left in enumerate(members):
            for right in members[i + 1:]:
                delta = float(target[left] - target[right])
                if abs(delta) > TIE_TOLERANCE:
                    rows.append((int(left), int(right), float(delta > 0), int(group)))
    return np.asarray(rows, dtype=np.float64)


def validate_registration(reg):
    if (reg["seed"] not in SEEDS or reg["held_fold"] not in (0, 1, 2, 3)
            or reg["updates"] != 3000 or reg["batch_size"] != 64
            or reg["learning_rate"] != 3e-4 or reg["width"] != 128
            or reg["hard_gpu_seconds"] > 900 or set(reg["source_sha256"]) != set(SOURCES)):
        raise ValueError("Frozen pairwise training contract changed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    reg = json.loads(args.registration.read_text())
    validate_registration(reg)
    code = Path(__file__).parent
    for name, digest in reg["source_sha256"].items():
        if sha256(code / name) != digest:
            raise RuntimeError("Frozen pairwise source changed: " + name)
    if reg["corpus_audit_sha256"] != sha256(Path(reg["corpus_audit"])):
        raise RuntimeError("Frozen independent corpus audit changed")
    audit = json.loads(Path(reg["corpus_audit"]).read_text())
    if audit["status"] != "PAIRWISE_CRITIC_CORPUS_AUDIT_PASS" or not audit["forbidden_input_arrays_absent"]:
        raise RuntimeError("Independent pairwise corpus audit missing")
    run = Path(reg["run_directory"])
    run.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        import torch
        from pairwise_model import PairwiseScore, pairwise_loss

        random.seed(reg["seed"]); np.random.seed(reg["seed"]); torch.manual_seed(reg["seed"])
        torch.cuda.manual_seed_all(reg["seed"]); torch.backends.cuda.matmul.allow_tf32 = False
        with np.load(reg["corpus"], allow_pickle=False) as saved:
            corpus = {key: saved[key].copy() for key in saved.files}
        if sha256(Path(reg["corpus"])) != reg["corpus_sha256"]:
            raise RuntimeError("Frozen pairwise corpus changed")
        meta = json.loads(Path(reg["metadata"]).read_text())
        if sha256(Path(reg["metadata"])) != reg["metadata_sha256"]:
            raise RuntimeError("Pairwise metadata changed")
        group_fold = {index: meta["fold_assignment"][row["episode_id"]]
                      for index, row in enumerate(meta["groups"])}
        train_groups = np.asarray([g for g in group_fold if group_fold[g] != reg["held_fold"]])
        held_groups = np.asarray([g for g in group_fold if group_fold[g] == reg["held_fold"]])
        train_rows = np.flatnonzero(np.isin(corpus["group_index"], train_groups))
        mean = corpus["state"][train_rows].mean(0).astype(np.float32)
        scale = np.maximum(corpus["state"][train_rows].std(0), 1e-5).astype(np.float32)
        state = ((corpus["state"] - mean) / scale).astype(np.float32)
        pairs = pair_indices(corpus["group_index"], corpus["target32"])
        train_pairs = pairs[np.isin(pairs[:, 3].astype(int), train_groups)]
        held_pairs = pairs[np.isin(pairs[:, 3].astype(int), held_groups)]
        if not len(train_pairs) or not len(held_pairs):
            raise RuntimeError("Empty registered pairwise split")
        generator = np.random.default_rng(reg["seed"])
        permutation = np.arange(len(corpus["action"]), dtype=np.int64)
        for group in np.unique(corpus["group_index"]):
            members = np.flatnonzero(corpus["group_index"] == group)
            permutation[members] = generator.permutation(members)
        models = {name: PairwiseScore(state.shape[1], width=128).cuda() for name in MODELS}
        initial = models["action_aware"].state_dict()
        for name in MODELS[1:]: models[name].load_state_dict(initial)
        optimizers = {name: torch.optim.Adam(model.parameters(), lr=3e-4) for name, model in models.items()}
        state_t = torch.as_tensor(state, device="cuda")
        action_t = torch.as_tensor(corpus["action"], device="cuda")
        zero_action = torch.zeros_like(action_t)
        perm_action = action_t[torch.as_tensor(permutation, device="cuda")]
        timings = []
        for update in range(1, 3001):
            if time.monotonic() - started >= reg["hard_gpu_seconds"]:
                raise RuntimeError("Registered pairwise worker time exhausted")
            chosen = train_pairs[generator.integers(0, len(train_pairs), size=64)]
            left = torch.as_tensor(chosen[:, 0].astype(int), device="cuda")
            right = torch.as_tensor(chosen[:, 1].astype(int), device="cuda")
            target = torch.as_tensor(chosen[:, 2], device="cuda", dtype=torch.float32)
            torch.cuda.synchronize(); tick = time.monotonic()
            for name, model in models.items():
                supplied = zero_action if name == "state_only" else perm_action if name == "permutation" else action_t
                loss = pairwise_loss(model, state_t[left], supplied[left], supplied[right], target)
                optimizers[name].zero_grad(set_to_none=True); loss.backward(); optimizers[name].step()
            torch.cuda.synchronize(); timings.append(time.monotonic() - tick)
            if update == 200:
                p90 = float(np.quantile(timings[50:], .9))
                forecast = (time.monotonic() - started) + (3000 - 200) * p90 + 20
                (run / "COST_FORECAST.json").write_text(json.dumps({
                    "step_p90_seconds": p90, "predicted_worker_seconds": forecast,
                    "cost_gate_pass": forecast <= reg["hard_gpu_seconds"],
                    "performance_metrics_used_for_stopping": False}, indent=2))
                if forecast > reg["hard_gpu_seconds"]: raise RuntimeError("Cost gate failed")
            if update % 500 == 0: print("fixed_update", update, flush=True)
        held = held_pairs.astype(np.float64)
        left = torch.as_tensor(held[:, 0].astype(int), device="cuda")
        right = torch.as_tensor(held[:, 1].astype(int), device="cuda")
        predictions = {}
        with torch.no_grad():
            for name, model in models.items():
                supplied = zero_action if name == "state_only" else perm_action if name == "permutation" else action_t
                predictions[name] = (model(state_t[left], supplied[left]) - model(state_t[right], supplied[right])).cpu().numpy()
            alternate = action_t[right]
            true_score = models["action_aware"](state_t[left], action_t[left])
            alternate_score = models["action_aware"](state_t[left], alternate)
            sensitivity = (true_score - alternate_score).abs().cpu().numpy()
        np.savez_compressed(run / "HELD_PREDICTIONS.npz", target=held[:, 2].astype(np.float32),
            group_index=held[:, 3].astype(np.int64), left=held[:, 0].astype(np.int64),
            right=held[:, 1].astype(np.int64), sensitivity=sensitivity,
            **{name: value.astype(np.float32) for name, value in predictions.items()})
        np.savez_compressed(run / "NORMALIZER.npz", mean=mean, scale=scale)
        torch.save({name: model.state_dict() for name, model in models.items()}, run / "FINAL_3000.pt")
        report = {"status": "PAIRWISE_CRITIC_WORKER_COMPLETE_NOT_QUALIFICATION",
            "seed": reg["seed"], "held_fold": reg["held_fold"], "updates": 3000,
            "training_groups": train_groups.tolist(), "held_groups": held_groups.tolist(),
            "held_pairs": int(len(held_pairs)), "wall_seconds": time.monotonic() - started,
            "peak_cuda_bytes": int(torch.cuda.max_memory_allocated()),
            "checkpoint_sha256": sha256(run / "FINAL_3000.pt"), "qualification": None}
        (run / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
        (run / "WORKER_COMPLETE").touch()
    except BaseException:
        (run / "FAILED.txt").write_text(traceback.format_exc())
        raise


if __name__ == "__main__": main()
