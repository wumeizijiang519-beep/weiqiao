"""Construct native plus outcome-blind ensemble-disagreement projections."""

import hashlib
import importlib.util
from pathlib import Path

import numpy as np

NORMALIZED_BOUND = 5.0
CHECKPOINT_SHA = {
    202642301: "253d63e66ec4a514f61e84e9fe92194c95f1fdf5e8dc2ddb154f933817ffacb9",
    202642302: "ab16c704cf11a017af53a2a9c25b4e16e77b57cfc509686d73bfd20047559c77",
    202642303: "903891dc2c4f318c188a196d537c59322fa8b0cf89f16084ca4220a48479536c",
}
_MODELS = None


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def normalized_executed_action(native, scale, offset):
    value = np.asarray(native, dtype=np.float32).copy()
    if value.shape[-1] != 7 or not np.isin(value[..., -1], [-1, 0, 1]).all():
        raise RuntimeError("Invalid native action")
    value[..., -1] = (1 - value[..., -1]) / 2
    return (value * scale + offset).astype(np.float32)


def native_from_normalized(value, scale, offset):
    result = ((np.asarray(value, dtype=np.float32) - offset) / scale).astype(np.float32)
    result[..., -1] = np.sign(1 - 2 * result[..., -1])
    return result


def models():
    global _MODELS
    if _MODELS is not None:
        return _MODELS
    import torch

    root = Path("/public/wangsenbao221/pqr/qgf_mainstream_20261022")
    spec = importlib.util.spec_from_file_location(
        "action_prefix_train", root / "action_prefix_pretrain_v1/train.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    result = []
    for seed, digest in CHECKPOINT_SHA.items():
        path = root / f"action_prefix_pretrain_v1/checkpoints_retry1/seed_{seed}/encoder.pt"
        if sha(path) != digest:
            raise RuntimeError("Frozen action encoder changed")
        payload = torch.load(path, map_location="cpu")
        model = module.ActionEncoder()
        model.load_state_dict(payload["model"])
        model.eval().to(device)
        for parameter in model.parameters():
            parameter.requires_grad_(False)
        result.append(model)
    _MODELS = (result, device)
    return _MODELS


def build_bank(native4, raw4, scale, offset, basis, median_norm, p95_norm):
    import torch

    native4 = np.asarray(native4, dtype=np.float32)
    raw4 = np.asarray(raw4, dtype=np.float32)
    scale = np.asarray(scale, dtype=np.float32)
    offset = np.asarray(offset, dtype=np.float32)
    if native4.shape != (4, 32, 7) or raw4.shape != native4.shape:
        raise RuntimeError("Native N4 shape mismatch")
    if not 0 < median_norm <= p95_norm:
        raise RuntimeError("Invalid support radius")
    normalized4 = normalized_executed_action(native4, scale, offset)
    ensemble, device = models()
    candidate = torch.tensor(normalized4[0], device=device, requires_grad=True)
    mask = torch.zeros((1, 32), dtype=torch.bool, device=device)
    mask[:, ::3] = True
    predictions = torch.stack([model(candidate[None], mask)[mask] for model in ensemble])
    disagreement = predictions.var(dim=0, unbiased=False).mean()
    gradient = torch.autograd.grad(disagreement, candidate)[0].detach().cpu().numpy().astype(np.float32)
    direction = -gradient[:, :6]
    norm = float(np.linalg.norm(direction.reshape(-1)))
    if not np.isfinite(norm) or norm <= 1e-12:
        raise RuntimeError("Degenerate disagreement gradient")
    direction /= norm
    guided = []
    realized = []
    for fraction in (0.25, 0.50, 0.75, 1.00):
        value = normalized4[0].copy()
        value[:, :6] = np.clip(
            value[:, :6] + direction * (median_norm * fraction),
            -NORMALIZED_BOUND,
            NORMALIZED_BOUND,
        )
        value[:, 6] = normalized4[0, :, 6]
        delta = float(np.linalg.norm((value[:, :6] - normalized4[0, :, :6]).reshape(-1)))
        if delta <= 0 or delta > p95_norm + 1e-6:
            raise RuntimeError("Projected candidate left support radius")
        guided.append(value)
        realized.append(delta)
    normalized8 = np.concatenate((normalized4, np.stack(guided))).astype(np.float32)
    native8 = np.concatenate((native4, native_from_normalized(np.stack(guided), scale, offset))).astype(np.float32)
    raw8 = np.concatenate((raw4, np.stack(guided))).astype(np.float32)
    hashes = [array_sha(value) for value in native8]
    if len(set(hashes)) != 8 or not np.array_equal(
        native8[4:, :, 6], np.broadcast_to(native4[0, :, 6], (4, 32))
    ):
        raise RuntimeError("Invalid projected bank")
    return {
        "native": native8,
        "raw_normalized": raw8,
        "executed_normalized": normalized8,
        "hashes": hashes,
        "structured_delta_norms": realized,
    }
