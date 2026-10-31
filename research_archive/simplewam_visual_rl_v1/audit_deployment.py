"""Zero-robot-action deployment audit using frozen corpus tensors."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from simplewam_visual_rl.deployment import FrozenVisualQ, QGFConfig


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_text())
    errors = []
    for item in registration["critic_checkpoints"]:
        if sha256(Path(item["path"])) != item["sha256"]:
            errors.append(f"critic hash mismatch: {item['seed']}/{item['fold']}")
    token = Path(registration["token_checkpoint"])
    if sha256(token) != registration["token_checkpoint_sha256"]:
        errors.append("token checkpoint hash mismatch")
    config = QGFConfig(**{
        key: registration["qgf"][key] for key in (
            "execution_horizon", "action_dim", "continuous_dims", "weight",
            "max_grad_norm", "sigma_min", "sigma_max",
        )
    })
    runtime = FrozenVisualQ(
        token, [item["path"] for item in registration["critic_checkpoints"]], "cuda",
        registration["support_min"], registration["support_max"], config,
    )
    corpus_path = Path(registration["online_validation"]["cohort_manifest"]).parents[1] / ".." / "simplewam_visual_rl_v1/critic_corpus_v1/CORPUS.npz"
    corpus_path = corpus_path.resolve()
    with np.load(corpus_path, allow_pickle=False) as archive:
        state = torch.from_numpy(np.concatenate((archive["token"][:1].astype(np.float32), archive["proprio"][:1]), axis=1)).cuda()
        prefixes = torch.from_numpy(archive["action_prefix"][:4]).cuda()
    bank = torch.zeros(4, 32, 7, device="cuda")
    bank[:, :10] = prefixes
    chosen, scores, index = runtime.rerank(state, bank)
    if chosen.shape != (1, 32, 7) or not 0 <= index < 4 or not torch.isfinite(scores).all():
        errors.append("rerank contract failed")
    velocity = torch.zeros_like(bank[:1])
    guided, diagnostics = runtime.guide_velocity(state, bank[:1], velocity, 0.0)
    if not diagnostics.get("applied"):
        errors.append(f"guidance inactive: {diagnostics}")
    if not torch.equal(guided[:, 10:], velocity[:, 10:]):
        errors.append("QGF modified the suffix")
    if not torch.equal(guided[:, :10, 6:], velocity[:, :10, 6:]):
        errors.append("QGF modified the gripper")
    if torch.equal(guided[:, :10, :6], velocity[:, :10, :6]):
        errors.append("QGF continuous gradient is identically zero")
    frozen_parameters = list(runtime.encoder.parameters())
    for critic in runtime.critics:
        frozen_parameters.extend(critic.parameters())
    if any(parameter.requires_grad or parameter.grad is not None for parameter in frozen_parameters):
        errors.append("frozen model received parameter gradients")
    status = "SIMPLEWAM_VISUAL_QGF_DEPLOYMENT_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_QGF_DEPLOYMENT_AUDIT_FAILED"
    report = {
        "status": status, "errors": errors, "registration_sha256": sha256(args.registration),
        "rerank_index": index, "rerank_scores": scores.cpu().tolist(),
        "guidance": diagnostics, "robot_actions_executed": 0, "wam_parameters_loaded": 0,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2))
    (args.output / status).touch()
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
