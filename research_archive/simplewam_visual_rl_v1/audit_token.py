"""Independent fail-closed audit for the outcome-blind RL-token checkpoint."""

import argparse
import hashlib
import json
from pathlib import Path

import torch


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    registration = json.loads(args.registration.read_text())
    report = json.loads((args.run / "REPORT.json").read_text())
    errors = []
    if registration.get("status") != "SIMPLEWAM_RL_TOKEN_TRAINING_REGISTERED":
        errors.append("registration status mismatch")
    if report.get("status") != "SIMPLEWAM_RL_TOKEN_TRAINING_COMPLETE":
        errors.append("training status mismatch")
    checkpoint_path = args.run / "TOKEN.pt"
    checkpoint_hash = sha256(checkpoint_path)
    if checkpoint_hash != report.get("checkpoint_sha256"):
        errors.append("checkpoint hash mismatch")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    if checkpoint.get("registration_sha256") != sha256(args.registration):
        errors.append("checkpoint registration receipt mismatch")
    if checkpoint.get("seed") != registration.get("seed"):
        errors.append("seed mismatch")
    if checkpoint.get("updates") != registration.get("updates"):
        errors.append("update count mismatch")
    if checkpoint.get("model_config") != registration.get("model"):
        errors.append("model configuration mismatch")
    if report.get("reward_fields_read") != 0 or report.get("success_fields_read") != 0:
        errors.append("outcome fields were read during token training")
    if report.get("critic_updates") != 0:
        errors.append("critic updates occurred during token training")
    state = checkpoint.get("model", {})
    if not state:
        errors.append("empty model state")
    elif any(not torch.isfinite(value).all() for value in state.values() if value.is_floating_point()):
        errors.append("nonfinite checkpoint tensor")
    if not (checkpoint.get("training_rows", 0) > checkpoint.get("validation_rows", 0) > 0):
        errors.append("invalid outcome-independent train/validation split")

    audit = {
        "status": "SIMPLEWAM_RL_TOKEN_AUDIT_PASS" if not errors else "SIMPLEWAM_RL_TOKEN_AUDIT_FAILED",
        "errors": errors,
        "checkpoint_sha256": checkpoint_hash,
        "registration_sha256": sha256(args.registration),
        "training_rows": checkpoint.get("training_rows"),
        "validation_rows": checkpoint.get("validation_rows"),
        "updates": checkpoint.get("updates"),
        "reward_fields_read": report.get("reward_fields_read"),
        "success_fields_read": report.get("success_fields_read"),
        "critic_updates": report.get("critic_updates"),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(audit, indent=2))
    (args.output / audit["status"]).touch()
    print(json.dumps(audit, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
