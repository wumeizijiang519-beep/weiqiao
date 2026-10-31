"""Freeze three full-data final critic registrations."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "simplewam_visual_rl_v1"
    corpus = base / "critic_corpus_v1/CORPUS.npz"
    token = base / "token_training_v1/TOKEN.pt"
    expected_corpus = "a2337827258238d6369a0161179491ffe3629b04f113cea9c0ab3d84a56e62b0"
    expected_token = "40a436a09e618965642f680bda5d1339f3426ccd735b73aba6629fbbc46a8c97"
    if sha256(corpus) != expected_corpus or sha256(token) != expected_token:
        raise RuntimeError("frozen input hash mismatch")
    args.output.mkdir(parents=True, exist_ok=False)
    workers = []
    for seed in (202644201, 202644202, 202644203):
        registration = {
            "status": "SIMPLEWAM_VISUAL_IQL_FINAL_REGISTERED",
            "branch": "full_data_final_critic_retrain_v1",
            "seed": seed,
            "corpus": str(corpus),
            "corpus_sha256": expected_corpus,
            "token_checkpoint_sha256": expected_token,
            "required_rows": 12218,
            "uses_all_training_rows": True,
            "heldout_fold": None,
            "validation_or_online_outcomes_read": 0,
            "training": {
                "updates": 50000,
                "batch_size": 64,
                "hidden_dim": 512,
                "learning_rate": 0.0003,
                "gamma": 0.99,
                "expectile": 0.7,
                "target_rate": 0.005,
                "parameter_grad_norm": 10.0,
            },
        }
        path = args.output / ("seed_%d.json" % seed)
        path.write_text(json.dumps(registration, indent=2, sort_keys=True))
        workers.append({"seed": seed, "registration": str(path), "sha256": sha256(path)})
    manifest = {
        "status": "SIMPLEWAM_VISUAL_IQL_FINAL_REGISTRATIONS_FROZEN",
        "workers": workers,
    }
    (args.output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

