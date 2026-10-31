"""Create the fixed twelve-worker pairwise critic registration."""

import argparse
import hashlib
import json
from pathlib import Path


SEEDS = (202641601, 202641602, 202641603)
SOURCES = ("train_pairwise_fold.py", "pairwise_model.py", "pairwise_corpus.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    registrations = output / "registrations"
    registrations.mkdir()
    corpus = root / "pairwise_critic_corpus_v1" / "CORPUS.npz"
    metadata = root / "pairwise_critic_corpus_v1" / "METADATA.json"
    audit = root / "pairwise_critic_corpus_audit_v1_retry2" / "REPORT.json"
    source = {name: sha(root / name) for name in SOURCES}
    rows = []
    for seed in SEEDS:
        for fold in range(4):
            stem = f"seed_{seed}_fold_{fold}"
            registration = {
                "status": "PAIRWISE_CRITIC_FIXED_WORKER_AUTHORIZED",
                "seed": seed, "held_fold": fold, "updates": 3000,
                "batch_size": 64, "learning_rate": 3e-4, "width": 128,
                "hard_gpu_seconds": 900,
                "corpus": str(corpus), "corpus_sha256": sha(corpus),
                "metadata": str(metadata), "metadata_sha256": sha(metadata),
                "corpus_audit": str(audit), "corpus_audit_sha256": sha(audit),
                "source_sha256": source,
                "run_directory": str(output / "runs" / stem),
                "online_qgf_efficacy": None,
            }
            path = registrations / f"{stem}.json"
            path.write_text(json.dumps(registration, indent=2, sort_keys=True))
            rows.append({"worker": stem, "registration_sha256": sha(path)})
    manifest = {
        "status": "PAIRWISE_CRITIC_12_WORKERS_AUTHORIZED",
        "user_authorization": "2026-10-28 direct training authorization",
        "workers": rows, "seeds": list(SEEDS), "folds": 4,
        "models_per_worker": ["action_aware", "state_only", "permutation"],
        "updates": 3000, "total_hard_gpu_seconds": 10800,
        "scientific_early_stopping": False, "online_qgf_efficacy": None,
    }
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__": main()
