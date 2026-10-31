"""Construct the frozen native-plus-support N8 bank without environment access."""

import hashlib

import numpy as np

NATIVE_SEEDS = (10000, 11000, 12000, 13000)
NORMALIZED_BOUND = 5.0


def array_sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def normalized_executed_action(native, scale, offset):
    value = np.asarray(native, dtype=np.float32).copy()
    if value.shape[-1] != 7 or not np.isin(value[..., -1], [-1, 0, 1]).all():
        raise RuntimeError("Invalid official native action")
    value[..., -1] = (1 - value[..., -1]) / 2
    return (value * scale + offset).astype(np.float32)


def native_from_normalized(value, scale, offset):
    result = ((np.asarray(value, dtype=np.float32) - offset) / scale).astype(np.float32)
    result[..., -1] = np.sign(1 - 2 * result[..., -1])
    return result


def build_bank(native4, raw4, scale, offset, basis, median_norm, p95_norm):
    native4 = np.asarray(native4, dtype=np.float32)
    raw4 = np.asarray(raw4, dtype=np.float32)
    scale = np.asarray(scale, dtype=np.float32)
    offset = np.asarray(offset, dtype=np.float32)
    basis = np.asarray(basis, dtype=np.float32)
    if native4.shape != (4, 32, 7) or raw4.shape != native4.shape:
        raise RuntimeError("Native N4 shape mismatch")
    if basis.shape != (3, 32, 6) or not np.isfinite(basis).all():
        raise RuntimeError("Support basis shape mismatch")
    if not np.isfinite(native4).all() or not np.isfinite(raw4).all():
        raise RuntimeError("Non-finite native bank")
    if not np.isin(native4[..., -1], [-1, 0, 1]).all():
        raise RuntimeError("Invalid native gripper")
    if not 0 < median_norm <= p95_norm:
        raise RuntimeError("Invalid frozen support radii")
    normalized4 = normalized_executed_action(native4, scale, offset)
    structured_normalized = []
    base = normalized4[0].copy()
    for direction in (basis[0], -basis[0], basis[1], -basis[1]):
        vector = direction.reshape(-1).astype(np.float64)
        norm = float(np.linalg.norm(vector))
        if not np.isfinite(norm) or norm <= 1e-12:
            raise RuntimeError("Degenerate support direction")
        delta = (direction / norm * median_norm).astype(np.float32)
        candidate = base.copy()
        candidate[:, :6] = np.clip(candidate[:, :6] + delta,
                                   -NORMALIZED_BOUND, NORMALIZED_BOUND)
        candidate[:, 6] = base[:, 6]
        realized = float(np.linalg.norm((candidate[:, :6] - base[:, :6]).reshape(-1)))
        if realized <= 0 or realized > p95_norm + 1e-6:
            raise RuntimeError("Structured candidate left frozen support radius")
        structured_normalized.append(candidate)
    normalized8 = np.concatenate([normalized4, np.stack(structured_normalized)], axis=0)
    native_structured = native_from_normalized(np.stack(structured_normalized), scale, offset)
    native8 = np.concatenate([native4, native_structured], axis=0).astype(np.float32)
    raw8 = np.concatenate([raw4, np.stack(structured_normalized)], axis=0).astype(np.float32)
    if native8.shape != (8, 32, 7) or normalized8.shape != native8.shape:
        raise RuntimeError("N8 construction shape mismatch")
    if not np.array_equal(native8[4:, :, 6], np.broadcast_to(native4[0, :, 6], (4, 32))):
        raise RuntimeError("Structured candidates changed gripper")
    hashes = [array_sha(candidate) for candidate in native8]
    if len(set(hashes)) != 8:
        raise RuntimeError("N8 bank is not unique")
    return {
        "native": native8,
        "raw_normalized": raw8,
        "executed_normalized": normalized8.astype(np.float32),
        "hashes": hashes,
        "structured_delta_norms": [
            float(np.linalg.norm((normalized8[i, :, :6] - normalized8[0, :, :6]).reshape(-1)))
            for i in range(4, 8)
        ],
    }
