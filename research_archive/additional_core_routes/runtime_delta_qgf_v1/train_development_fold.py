"""Fixed Runtime-Delta development OOF worker with matched controls."""

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


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
        from delta_model import ActionOnlyPredictor, RuntimeDeltaPredictor, StateOnlyPredictor

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
        held_rows = np.flatnonzero(np.isin(corpus["group_index"], held_groups))
        state_mean = corpus["state"][train_rows].mean(0).astype(np.float32)
        state_scale = np.maximum(corpus["state"][train_rows].std(0), 1e-5).astype(np.float32)
        target_mean = corpus["target_components"][train_rows].mean(0).astype(np.float32)
        target_scale = np.maximum(corpus["target_components"][train_rows].std(0), 1e-4).astype(np.float32)
        state = ((corpus["state"] - state_mean) / state_scale).astype(np.float32)
        target = ((corpus["target_components"] - target_mean) / target_scale).astype(np.float32)
        generator = np.random.default_rng(reg["seed"] + reg["held_fold"] * 1009)
        permutation = np.arange(len(corpus["action"]), dtype=np.int64)
        for group in range(24):
            members = np.flatnonzero(corpus["group_index"] == group)
            permutation[members] = generator.permutation(members)
        state_t = torch.as_tensor(state, device="cuda")
        action_t = torch.as_tensor(corpus["action"], device="cuda")
        perm_action_t = action_t[torch.as_tensor(permutation, device="cuda")]
        target_t = torch.as_tensor(target, device="cuda")
        models = {
            "proposed": RuntimeDeltaPredictor(state.shape[1]).cuda(),
            "permutation": RuntimeDeltaPredictor(state.shape[1]).cuda(),
            "state_only": StateOnlyPredictor(state.shape[1]).cuda(),
            "action_only": ActionOnlyPredictor(state.shape[1]).cuda(),
        }
        optimizers = {name: torch.optim.Adam(model.parameters(), lr=3e-4) for name, model in models.items()}
        for update in range(1, UPDATES + 1):
            if time.monotonic() - started > reg["hard_gpu_seconds"]:
                raise RuntimeError("Worker time exhausted")
            selected_np = generator.choice(train_rows, size=128, replace=True)
            selected = torch.as_tensor(selected_np, device="cuda")
            for name, model in models.items():
                supplied = perm_action_t if name == "permutation" else action_t
                prediction = model(state_t[selected], supplied[selected])
                loss = torch.nn.functional.mse_loss(prediction, target_t[selected])
                optimizers[name].zero_grad(set_to_none=True); loss.backward(); optimizers[name].step()
            if update % 500 == 0:
                print("fixed_update", update, flush=True)
        predictions = {}
        held = torch.as_tensor(held_rows, device="cuda")
        target_mean_t = torch.as_tensor(target_mean, device="cuda")
        target_scale_t = torch.as_tensor(target_scale, device="cuda")
        with torch.no_grad():
            for name, model in models.items():
                supplied = perm_action_t if name == "permutation" else action_t
                normalized = model(state_t[held], supplied[held])
                predictions[name] = (normalized * target_scale_t + target_mean_t).cpu().numpy()
            proposed = models["proposed"](state_t[held], action_t[held])
            cyclic_index = []
            for row in held_rows:
                group = int(corpus["group_index"][row])
                candidate = int(corpus["candidate_index"][row])
                members = np.flatnonzero(corpus["group_index"] == group)
                cyclic_index.append(members[(candidate + 1) % 8])
            cyclic = models["proposed"](state_t[held], action_t[torch.as_tensor(cyclic_index, device="cuda")])
            sensitivity = ((proposed - cyclic) * target_scale_t).abs().mean(1).cpu().numpy()
        np.savez_compressed(
            run / "HELD_PREDICTIONS.npz",
            target_components=corpus["target_components"][held_rows].astype(np.float32),
            target_scalar=corpus["target_scalar"][held_rows].astype(np.float32),
            group_index=corpus["group_index"][held_rows].astype(np.int64),
            candidate_index=corpus["candidate_index"][held_rows].astype(np.int64),
            sensitivity=sensitivity.astype(np.float32),
            **{name: value.astype(np.float32) for name, value in predictions.items()},
        )
        np.savez_compressed(run / "NORMALIZER.npz", state_mean=state_mean, state_scale=state_scale,
                            target_mean=target_mean, target_scale=target_scale)
        torch.save({name: model.state_dict() for name, model in models.items()}, run / "FINAL_3000.pt")
        report = {
            "status": "RUNTIME_DELTA_DEVELOPMENT_WORKER_COMPLETE",
            "seed": reg["seed"], "held_fold": reg["held_fold"], "updates": UPDATES,
            "held_rows": int(len(held_rows)), "held_groups": held_groups.tolist(),
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
