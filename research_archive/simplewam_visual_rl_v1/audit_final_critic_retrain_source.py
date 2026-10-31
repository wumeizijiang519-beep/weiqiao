"""Fail-closed audit of the final critic retraining contract."""

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
    parser.add_argument("--registrations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.registrations / "MANIFEST.json").read_text())
    errors = []
    expected_seeds = [202644201, 202644202, 202644203]
    seen = []
    for worker in manifest.get("workers", []):
        path = Path(worker["registration"])
        registration = json.loads(path.read_text())
        seen.append(registration.get("seed"))
        training = registration.get("training", {})
        checks = {
            "registration hash": sha256(path) == worker.get("sha256"),
            "full data": registration.get("uses_all_training_rows") is True,
            "no heldout fold": registration.get("heldout_fold") is None,
            "no outcome read": registration.get("validation_or_online_outcomes_read") == 0,
            "rows": registration.get("required_rows") == 12218,
            "updates": training.get("updates") == 50000,
            "batch": training.get("batch_size") == 64,
            "hidden": training.get("hidden_dim") == 512,
            "lr": training.get("learning_rate") == 0.0003,
            "gamma": training.get("gamma") == 0.99,
            "expectile": training.get("expectile") == 0.7,
            "target rate": training.get("target_rate") == 0.005,
        }
        errors.extend("seed %s: %s" % (registration.get("seed"), name) for name, ok in checks.items() if not ok)
    if sorted(seen) != expected_seeds:
        errors.append("seed set mismatch")
    trainer = args.root / "simplewam_visual_rl_v1/train_visual_iql_final.py"
    protocol = args.root / "simplewam_visual_rl_v1/FINAL_CRITIC_RETRAIN_PROTOCOL.md"
    status = "SIMPLEWAM_VISUAL_IQL_FINAL_SOURCE_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_IQL_FINAL_SOURCE_AUDIT_FAIL"
    report = {
        "status": status,
        "errors": errors,
        "worker_count": len(seen),
        "trainer_sha256": sha256(trainer),
        "protocol_sha256": sha256(protocol),
        "manifest_sha256": sha256(args.registrations / "MANIFEST.json"),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / status).touch()
    print(json.dumps(report, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

