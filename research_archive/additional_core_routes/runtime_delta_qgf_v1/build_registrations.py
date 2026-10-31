"""Freeze nine Runtime-Delta development workers."""

import argparse
import hashlib
import json
from pathlib import Path


SEEDS = (202642301, 202642302, 202642303)
SOURCES = ("train_development_fold.py", "delta_model.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    code = args.root / "runtime_delta_qgf_v1"
    args.output.mkdir(parents=True, exist_ok=False)
    registrations = args.output / "registrations"
    registrations.mkdir()
    corpus = code / "development_corpus_v1"
    source = {name: sha(code / name) for name in SOURCES}
    workers = []
    for seed in SEEDS:
        for fold in range(3):
            stem = f"seed_{seed}_fold_{fold}"
            registration = {
                "seed": seed, "held_fold": fold, "updates": 3000,
                "hard_gpu_seconds": 900,
                "corpus": str(corpus / "CORPUS.npz"),
                "corpus_sha256": sha(corpus / "CORPUS.npz"),
                "metadata": str(corpus / "METADATA.json"),
                "metadata_sha256": sha(corpus / "METADATA.json"),
                "corpus_audit": str(code / "development_corpus_audit_v1/REPORT.json"),
                "corpus_audit_sha256": sha(code / "development_corpus_audit_v1/REPORT.json"),
                "source_sha256": source,
                "run_directory": str(args.output / "runs" / stem),
                "confirmation_labels_read": False,
            }
            path = registrations / f"{stem}.json"
            path.write_text(json.dumps(registration, indent=2, sort_keys=True))
            workers.append({"worker": stem, "registration_sha256": sha(path)})
    manifest = {
        "status": "RUNTIME_DELTA_9_WORKERS_AUTHORIZED",
        "seeds": list(SEEDS), "folds": 3, "workers": workers,
        "models": ["proposed", "state_only", "permutation", "action_only"],
        "updates": 3000, "total_hard_gpu_seconds": 8100,
        "confirmation_labels_read": False, "scientific_early_stopping": False,
    }
    (args.output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
