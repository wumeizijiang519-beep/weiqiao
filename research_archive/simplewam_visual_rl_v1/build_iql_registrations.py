"""Freeze the nine Simple-WAM visual-IQL worker registrations."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-report", type=Path, required=True)
    parser.add_argument("--corpus-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if json.loads(args.corpus_audit.read_text())["status"] != "SIMPLEWAM_VISUAL_RL_CRITIC_CORPUS_AUDIT_PASS":
        raise RuntimeError("audited corpus required")
    corpus = str(args.corpus_report.parent / "CORPUS.npz")
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {"status": "SIMPLEWAM_VISUAL_IQL_REGISTRATIONS_FROZEN", "workers": []}
    settings = {"updates": 3000, "batch_size": 256, "hidden_dim": 512, "learning_rate": 0.0003,
                "gamma": 0.99, "expectile": 0.7, "target_rate": 0.005}
    for seed in (202644201, 202644202, 202644203):
        for fold in (0, 1, 2):
            worker = f"seed_{seed}_fold_{fold}"
            registration = {
                "status": "SIMPLEWAM_VISUAL_IQL_WORKER_REGISTERED",
                "worker": worker, "seed": seed, "heldout_fold": fold,
                "corpus": corpus, "corpus_sha256": sha256(corpus),
                "corpus_audit_sha256": sha256(args.corpus_audit),
                "training": settings,
                "q_input": {"token_dim": 2048, "proprio_dim": 9, "planned_prefix": [10, 7], "realized_length": False},
                "controls": ["state_only", "within_physical_group_action_permutation"],
            }
            path = args.output / f"{worker}.json"
            path.write_text(json.dumps(registration, indent=2))
            manifest["workers"].append({"worker": worker, "registration": str(path), "sha256": sha256(path)})
    (args.output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    (args.output / manifest["status"]).touch()
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
