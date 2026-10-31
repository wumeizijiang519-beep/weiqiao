"""Fixed-update Runtime-Anchored critic worker with matched controls."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import traceback

import numpy as np

SEEDS = (202642301, 202642302, 202642303)
MODELS = ("action_aware", "state_only", "permutation")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pairs(group_index, target):
    rows = []
    for group in np.unique(group_index):
        members = np.flatnonzero(group_index == group)
        for i, left in enumerate(members):
            for right in members[i + 1:]:
                delta = float(target[left] - target[right])
                if abs(delta) > 1e-6:
                    rows.append((left, right, float(delta > 0), group))
    return np.asarray(rows, dtype=np.float64)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    reg = json.loads(args.registration.read_text())
    if reg["seed"] not in SEEDS or reg["held_fold"] not in (0, 1, 2) or reg["updates"] != 3000:
        raise RuntimeError("Training contract changed")
    code = Path(__file__).parent
    for name, digest in reg["source_sha256"].items():
        if sha(code / name) != digest:
            raise RuntimeError("Source changed: " + name)
    audit = json.loads(Path(reg["corpus_audit"]).read_text())
    if (sha(reg["corpus_audit"]) != reg["corpus_audit_sha256"]
            or audit["status"] != "RUNTIME_ANCHORED_CRITIC_CORPUS_AUDIT_PASS"):
        raise RuntimeError("Corpus audit missing")
    run = Path(reg["run_directory"])
    run.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        import torch
        from critic_model import ActionEncoder, PairwiseScore
        random.seed(reg["seed"]); np.random.seed(reg["seed"]); torch.manual_seed(reg["seed"])
        torch.cuda.manual_seed_all(reg["seed"]); torch.backends.cuda.matmul.allow_tf32 = False
        with np.load(reg["corpus"], allow_pickle=False) as saved:
            corpus = {key: saved[key].copy() for key in saved.files}
        meta = json.loads(Path(reg["metadata"]).read_text())
        if sha(reg["corpus"]) != reg["corpus_sha256"] or sha(reg["metadata"]) != reg["metadata_sha256"]:
            raise RuntimeError("Corpus changed")
        fold = {i: meta["fold_assignment"][row["episode_id"]] for i, row in enumerate(meta["groups"])}
        train_groups = np.asarray([g for g in fold if fold[g] != reg["held_fold"]])
        held_groups = np.asarray([g for g in fold if fold[g] == reg["held_fold"]])
        train_rows = np.flatnonzero(np.isin(corpus["group_index"], train_groups))
        mean = corpus["state"][train_rows].mean(0).astype(np.float32)
        scale = np.maximum(corpus["state"][train_rows].std(0), 1e-5).astype(np.float32)
        state = ((corpus["state"] - mean) / scale).astype(np.float32)
        all_pairs = pairs(corpus["group_index"], corpus["target"])
        train_pairs = all_pairs[np.isin(all_pairs[:, 3].astype(int), train_groups)]
        held_pairs = all_pairs[np.isin(all_pairs[:, 3].astype(int), held_groups)]
        if not len(train_pairs) or not len(held_pairs):
            raise RuntimeError("Empty pairwise split")
        encoder = ActionEncoder().cuda()
        checkpoint = torch.load(reg["encoder_checkpoint"], map_location="cuda", weights_only=True)
        encoder.load_state_dict(checkpoint["model"]); encoder.eval()
        with torch.no_grad():
            action_embedding = encoder.embed_prefix(torch.as_tensor(corpus["action"], device="cuda"))
        generator = np.random.default_rng(reg["seed"])
        permutation = np.arange(len(corpus["action"]), dtype=np.int64)
        for group in np.unique(corpus["group_index"]):
            members = np.flatnonzero(corpus["group_index"] == group)
            permutation[members] = generator.permutation(members)
        state_t = torch.as_tensor(state, device="cuda")
        perm_embedding = action_embedding[torch.as_tensor(permutation, device="cuda")]
        zero_embedding = torch.zeros_like(action_embedding)
        models = {name: PairwiseScore(state.shape[1]).cuda() for name in MODELS}
        initial = models["action_aware"].state_dict()
        for name in MODELS[1:]: models[name].load_state_dict(initial)
        optimizers = {name: torch.optim.Adam(model.parameters(), lr=3e-4) for name, model in models.items()}
        for update in range(1, 3001):
            if time.monotonic() - started > reg["hard_gpu_seconds"]:
                raise RuntimeError("Worker time exhausted")
            chosen = train_pairs[generator.integers(0, len(train_pairs), size=64)]
            left = torch.as_tensor(chosen[:, 0].astype(int), device="cuda")
            right = torch.as_tensor(chosen[:, 1].astype(int), device="cuda")
            target = torch.as_tensor(chosen[:, 2], device="cuda", dtype=torch.float32)
            for name, model in models.items():
                supplied = zero_embedding if name == "state_only" else perm_embedding if name == "permutation" else action_embedding
                logits = model(state_t[left], supplied[left]) - model(state_t[right], supplied[right])
                loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, target)
                optimizers[name].zero_grad(set_to_none=True); loss.backward(); optimizers[name].step()
            if update % 500 == 0: print("fixed_update", update, flush=True)
        held = held_pairs
        left = torch.as_tensor(held[:, 0].astype(int), device="cuda")
        right = torch.as_tensor(held[:, 1].astype(int), device="cuda")
        predictions = {}
        with torch.no_grad():
            for name, model in models.items():
                supplied = zero_embedding if name == "state_only" else perm_embedding if name == "permutation" else action_embedding
                predictions[name] = (model(state_t[left], supplied[left]) - model(state_t[right], supplied[right])).cpu().numpy()
            sensitivity = (models["action_aware"](state_t[left], action_embedding[left]) - models["action_aware"](state_t[left], action_embedding[right])).abs().cpu().numpy()
        np.savez_compressed(run / "HELD_PREDICTIONS.npz", target=held[:, 2].astype(np.float32),
            group_index=held[:, 3].astype(np.int64), sensitivity=sensitivity,
            **{name: value.astype(np.float32) for name, value in predictions.items()})
        np.savez_compressed(run / "NORMALIZER.npz", mean=mean, scale=scale)
        torch.save({name: model.state_dict() for name, model in models.items()}, run / "FINAL_3000.pt")
        report = {"status": "RUNTIME_ANCHORED_CRITIC_WORKER_COMPLETE", "seed": reg["seed"],
            "held_fold": reg["held_fold"], "updates": 3000, "held_pairs": int(len(held_pairs)),
            "wall_seconds": time.monotonic() - started, "checkpoint_sha256": sha(run / "FINAL_3000.pt")}
        (run / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
        (run / "WORKER_COMPLETE").touch()
    except BaseException:
        (run / "FAILED.txt").write_text(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
