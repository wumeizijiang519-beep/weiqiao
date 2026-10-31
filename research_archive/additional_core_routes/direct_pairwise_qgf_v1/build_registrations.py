"""Freeze nine Direct-Pairwise development workers."""

import argparse
import hashlib
import json
from pathlib import Path


SEEDS = (202642301, 202642302, 202642303)
SOURCES = ("train_fold.py", "pairwise_model.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    code = root / "direct_pairwise_qgf_v1"
    corpus = root / "runtime_delta_qgf_v1/development_corpus_v1"
    audit = root / "runtime_delta_qgf_v1/development_corpus_audit_v1/REPORT.json"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    registrations = output / "registrations"; registrations.mkdir()
    source = {name: sha(code / name) for name in SOURCES}
    workers = []
    for seed in SEEDS:
        for fold in range(3):
            stem = f"seed_{seed}_fold_{fold}"
            registration = {
                "seed": seed, "held_fold": fold, "updates": 3000, "hard_gpu_seconds": 900,
                "corpus": str(corpus / "CORPUS.npz"), "corpus_sha256": sha(corpus / "CORPUS.npz"),
                "metadata": str(corpus / "METADATA.json"), "metadata_sha256": sha(corpus / "METADATA.json"),
                "corpus_audit": str(audit), "corpus_audit_sha256": sha(audit),
                "source_sha256": source,
                "run_directory": str(output / "runs" / stem),
                "confirmation_labels_read": False,
            }
            path = registrations / f"{stem}.json"
            path.write_text(json.dumps(registration, indent=2, sort_keys=True))
            workers.append({"worker": stem, "registration_sha256": sha(path)})
    manifest = {
        "status": "DIRECT_PAIRWISE_9_WORKERS_AUTHORIZED", "seeds": list(SEEDS),
        "folds": 3, "workers": workers, "updates": 3000,
        "models": ["proposed", "state_only", "permutation", "action_only"],
        "confirmation_labels_read": False, "scientific_early_stopping": False,
    }
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
