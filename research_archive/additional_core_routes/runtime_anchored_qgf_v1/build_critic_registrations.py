"""Freeze nine Runtime-Anchored critic workers."""

import argparse
import hashlib
import json
from pathlib import Path

SEEDS = (202642301, 202642302, 202642303)
SOURCES = ("train_critic_fold.py", "critic_model.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    code = Path(__file__).parent.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    registrations = output / "registrations"
    registrations.mkdir()
    corpus_dir = code / "critic_corpus_v1"
    source = {name: sha(code / name) for name in SOURCES}
    workers = []
    for seed in SEEDS:
        encoder = code.parent / "action_prefix_pretrain_v1" / "checkpoints_retry1" / f"seed_{seed}" / "encoder.pt"
        for fold in range(3):
            stem = f"seed_{seed}_fold_{fold}"
            registration = {
                "seed": seed, "held_fold": fold, "updates": 3000,
                "hard_gpu_seconds": 600,
                "corpus": str(corpus_dir / "CORPUS.npz"),
                "corpus_sha256": sha(corpus_dir / "CORPUS.npz"),
                "metadata": str(corpus_dir / "METADATA.json"),
                "metadata_sha256": sha(corpus_dir / "METADATA.json"),
                "corpus_audit": str(code / "critic_corpus_audit_v1" / "REPORT.json"),
                "corpus_audit_sha256": sha(code / "critic_corpus_audit_v1" / "REPORT.json"),
                "encoder_checkpoint": str(encoder),
                "encoder_checkpoint_sha256": sha(encoder),
                "source_sha256": source,
                "run_directory": str(output / "runs" / stem),
            }
            path = registrations / f"{stem}.json"
            path.write_text(json.dumps(registration, indent=2, sort_keys=True))
            workers.append({"worker": stem, "registration_sha256": sha(path)})
    manifest = {"status": "RUNTIME_ANCHORED_CRITIC_9_WORKERS_AUTHORIZED",
                "seeds": list(SEEDS), "folds": 3, "workers": workers,
                "models": ["action_aware", "state_only", "permutation"],
                "updates": 3000, "total_hard_gpu_seconds": 5400,
                "scientific_early_stopping": False}
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
