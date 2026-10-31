"""Fixed development OOF worker for Setwise-Contrastive QGF V1."""

import argparse
import hashlib
import json
import random
import time
import traceback
from pathlib import Path

import numpy as np


SEEDS = (202642301, 202642302, 202642303)
MODELS = ("setwise", "state_only", "permutation", "independent")
UPDATES = 3000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pair_rows(group_indices, targets):
    rows = []
    for group in group_indices:
        for left in range(8):
            for right in range(left + 1, 8):
                delta = float(targets[group, left] - targets[group, right])
                if abs(delta) > 1e-6:
                    rows.append((group, left, right, float(delta > 0)))
    return np.asarray(rows, dtype=np.float64)


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
    if sha(reg["corpus_audit"]) != reg["corpus_audit_sha256"] or audit["status"] != "SETWISE_DEVELOPMENT_CORPUS_AUDIT_PASS":
        raise RuntimeError("Development corpus audit missing")
    run = Path(reg["run_directory"])
    run.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        import torch
        from setwise_model import ActionEncoder, IndependentScore, SetwiseScore, StateOnlyScore

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
        state = corpus["state"].reshape(12, 8, -1)[:, 0]
        actions = corpus["action"].reshape(12, 8, 16, 7)
        targets = corpus["target"].reshape(12, 8)
        mean = state[train_groups].mean(0).astype(np.float32)
        scale = np.maximum(state[train_groups].std(0), 1e-5).astype(np.float32)
        state = ((state - mean) / scale).astype(np.float32)
        train_pairs = pair_rows(train_groups, targets)
        held_pairs = pair_rows(held_groups, targets)
        if not len(train_pairs) or not len(held_pairs):
            raise RuntimeError("Empty pairwise split")

        encoder = ActionEncoder().cuda()
        checkpoint = torch.load(reg["encoder_checkpoint"], map_location="cuda", weights_only=True)
        encoder.load_state_dict(checkpoint["model"]); encoder.eval()
        with torch.no_grad():
            embedding = encoder.embed_prefix(torch.as_tensor(actions.reshape(-1, 16, 7), device="cuda")).reshape(12, 8, 128)
        generator = np.random.default_rng(reg["seed"] + reg["held_fold"] * 1009)
        permutation = np.stack([generator.permutation(8) for _ in range(12)])
        perm_embedding = embedding[torch.arange(12, device="cuda")[:, None], torch.as_tensor(permutation, device="cuda")]
        state_t = torch.as_tensor(state, device="cuda")
        models = {
            "setwise": SetwiseScore(state.shape[1]).cuda(),
            "permutation": SetwiseScore(state.shape[1]).cuda(),
            "independent": IndependentScore(state.shape[1]).cuda(),
            "state_only": StateOnlyScore(state.shape[1]).cuda(),
        }
        optimizers = {name: torch.optim.Adam(model.parameters(), lr=3e-4) for name, model in models.items()}
        for update in range(1, UPDATES + 1):
            if time.monotonic() - started > reg["hard_gpu_seconds"]:
                raise RuntimeError("Worker time exhausted")
            selected = train_pairs[generator.integers(0, len(train_pairs), size=64)]
            group = torch.as_tensor(selected[:, 0].astype(int), device="cuda")
            left = torch.as_tensor(selected[:, 1].astype(int), device="cuda")
            right = torch.as_tensor(selected[:, 2].astype(int), device="cuda")
            label = torch.as_tensor(selected[:, 3], device="cuda", dtype=torch.float32)
            for name, model in models.items():
                supplied = perm_embedding if name == "permutation" else embedding
                scores = model(state_t, supplied)
                logits = scores[group, left] - scores[group, right]
                loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, label)
                optimizers[name].zero_grad(set_to_none=True); loss.backward(); optimizers[name].step()
            if update % 500 == 0:
                print("fixed_update", update, flush=True)

        group = torch.as_tensor(held_pairs[:, 0].astype(int), device="cuda")
        left = torch.as_tensor(held_pairs[:, 1].astype(int), device="cuda")
        right = torch.as_tensor(held_pairs[:, 2].astype(int), device="cuda")
        predictions = {}
        with torch.no_grad():
            for name, model in models.items():
                supplied = perm_embedding if name == "permutation" else embedding
                scores = model(state_t, supplied)
                predictions[name] = (scores[group, left] - scores[group, right]).cpu().numpy()
            base = models["setwise"](state_t, embedding)
            cyclic = models["setwise"](state_t, embedding.roll(1, dims=1)).roll(-1, dims=1)
            sensitivity = (base - cyclic).abs().mean(1).cpu().numpy()
        np.savez_compressed(
            run / "HELD_PREDICTIONS.npz",
            target=held_pairs[:, 3].astype(np.float32),
            group_index=held_pairs[:, 0].astype(np.int64),
            sensitivity=sensitivity[held_groups].astype(np.float32),
            **{name: value.astype(np.float32) for name, value in predictions.items()},
        )
        np.savez_compressed(run / "NORMALIZER.npz", mean=mean, scale=scale)
        torch.save({name: model.state_dict() for name, model in models.items()}, run / "FINAL_3000.pt")
        report = {
            "status": "SETWISE_DEVELOPMENT_WORKER_COMPLETE",
            "seed": reg["seed"], "held_fold": reg["held_fold"], "updates": UPDATES,
            "held_pairs": int(len(held_pairs)), "held_groups": held_groups.tolist(),
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
