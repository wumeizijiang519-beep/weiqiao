"""Freeze nine family-balanced development OOF workers."""

import argparse
import hashlib
import json
from pathlib import Path


SEEDS = (202642301, 202642302, 202642303)
SOURCES = ("train_development_fold.py", "setwise_model.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    code = args.root / "setwise_contrastive_qgf_v1"
    args.output.mkdir(parents=True, exist_ok=False)
    registrations = args.output / "registrations"
    registrations.mkdir()
    corpus_dir = code / "development_corpus_v1"
    source = {name: sha(code / name) for name in SOURCES}
    workers = []
    for seed in SEEDS:
        encoder = args.root / "action_prefix_pretrain_v1/checkpoints_retry1" / f"seed_{seed}" / "encoder.pt"
        for fold in range(3):
            stem = f"seed_{seed}_fold_{fold}"
            registration = {
                "seed": seed,
                "held_fold": fold,
                "updates": 3000,
                "hard_gpu_seconds": 900,
                "corpus": str(corpus_dir / "CORPUS.npz"),
                "corpus_sha256": sha(corpus_dir / "CORPUS.npz"),
                "metadata": str(corpus_dir / "METADATA.json"),
                "metadata_sha256": sha(corpus_dir / "METADATA.json"),
                "corpus_audit": str(code / "development_corpus_audit_v1/REPORT.json"),
                "corpus_audit_sha256": sha(code / "development_corpus_audit_v1/REPORT.json"),
                "encoder_checkpoint": str(encoder),
                "encoder_checkpoint_sha256": sha(encoder),
                "source_sha256": source,
                "run_directory": str(args.output / "runs" / stem),
                "confirmation_labels_read": False,
            }
            path = registrations / f"{stem}.json"
            path.write_text(json.dumps(registration, indent=2, sort_keys=True))
            workers.append({"worker": stem, "registration_sha256": sha(path)})
    manifest = {
        "status": "SETWISE_DEVELOPMENT_9_WORKERS_AUTHORIZED",
        "seeds": list(SEEDS), "folds": 3, "workers": workers,
        "models": ["setwise", "state_only", "permutation", "independent"],
        "updates": 3000, "total_hard_gpu_seconds": 8100,
        "confirmation_labels_read": False, "scientific_early_stopping": False,
    }
    (args.output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
