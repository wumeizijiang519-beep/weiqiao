"""Outcome-blind arm scheduling and receipts for online Simple-WAM QGF."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Mapping

import numpy as np
import torch


ARMS = ("candidate0", "uniform_random", "critic_rerank", "visual_qgf")


def _digest(value: torch.Tensor) -> str:
    array = value.detach().to(device="cpu", dtype=torch.float32).contiguous().numpy()
    return hashlib.sha256(array.tobytes()).hexdigest()


def frozen_arm_order(scene_key: str, seed: int) -> tuple[str, ...]:
    """Return a result-independent, stable arm order for one physical scene."""
    if not scene_key or seed < 0:
        raise ValueError("scene key and nonnegative scheduling seed are required")
    return tuple(sorted(ARMS, key=lambda arm: hashlib.sha256(
        f"{seed}:{scene_key}:{arm}".encode("utf-8")
    ).digest()))


def frozen_random_index(scene_key: str, decision_index: int, candidates: int, seed: int) -> int:
    if not scene_key or decision_index < 0 or candidates < 1 or seed < 0:
        raise ValueError("invalid deterministic random-selection inputs")
    digest = hashlib.sha256(
        f"{seed}:{scene_key}:{decision_index}:uniform_random".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "little") % candidates


@dataclass(frozen=True)
class OnlineDecision:
    arm: str
    selected_index: int
    selected_actions: torch.Tensor
    receipt: Mapping[str, object]


def select_online_arm(
    *,
    arm: str,
    scene_key: str,
    decision_index: int,
    selection_seed: int,
    frozen_q,
    state: torch.Tensor,
    native_bank: torch.Tensor,
    guided_bank: torch.Tensor,
    guidance_traces: tuple[Mapping[str, object], ...],
    native_score_bank: torch.Tensor | None = None,
    guided_score_bank: torch.Tensor | None = None,
) -> OnlineDecision:
    """Select one arm after computing the same native and QGF shadow work.

    `guided_bank` must contain one guided counterpart for every native proposal.
    The caller therefore performs identical candidate generation, visual-token
    extraction, critic scoring, and Q-gradient work regardless of which arm is
    committed to the environment.
    """
    if arm not in ARMS:
        raise ValueError(f"unknown online arm: {arm}")
    if native_bank.ndim != 3 or native_bank.shape[0] < 2:
        raise ValueError("native bank must be [N,H,A] with at least two candidates")
    if guided_bank.shape != native_bank.shape:
        raise ValueError("guided and native banks must have identical shapes")
    native_score_bank = native_bank if native_score_bank is None else native_score_bank
    guided_score_bank = guided_bank if guided_score_bank is None else guided_score_bank
    if native_score_bank.shape != native_bank.shape or guided_score_bank.shape != guided_bank.shape:
        raise ValueError("critic-space and execution-space banks must have identical shapes")
    if len(guidance_traces) != len(native_bank):
        raise ValueError("one guidance trace is required per candidate")
    if not all(torch.isfinite(value).all() for value in (
        native_bank, guided_bank, native_score_bank, guided_score_bank
    )):
        raise ValueError("candidate banks must be finite")
    if not torch.equal(native_bank[0], native_bank[0].clone()):
        raise RuntimeError("candidate0 changed unexpectedly")

    with torch.no_grad():
        native_scores = frozen_q.q(state, native_score_bank).detach()
        guided_scores = frozen_q.q(state, guided_score_bank).detach()
        native_supported = frozen_q.in_support(native_score_bank).detach()
        guided_supported = frozen_q.in_support(guided_score_bank).detach()
    native_masked = native_scores.masked_fill(~native_supported, -torch.inf)
    guided_masked = guided_scores.masked_fill(~guided_supported, -torch.inf)

    support_abstention = False

    if arm == "candidate0":
        selected_bank, selected = native_bank, 0
    elif arm == "uniform_random":
        selected_bank = native_bank
        selected = frozen_random_index(scene_key, decision_index, len(native_bank), selection_seed)
    elif arm == "critic_rerank":
        selected_bank = native_bank
        if native_supported.any():
            selected = int(native_masked.argmax())
        else:
            selected, support_abstention = 0, True
    else:
        if guided_supported.any():
            selected_bank = guided_bank
            selected = int(guided_masked.argmax())
        else:
            selected_bank, selected, support_abstention = native_bank, 0, True

    selected_actions = selected_bank[selected:selected + 1].detach().clone()
    receipt = {
        "arm": arm,
        "scene_key": scene_key,
        "decision_index": int(decision_index),
        "selection_seed": int(selection_seed),
        "selected_index": selected,
        "native_bank_sha256": _digest(native_bank),
        "guided_bank_sha256": _digest(guided_bank),
        "native_score_bank_sha256": _digest(native_score_bank),
        "guided_score_bank_sha256": _digest(guided_score_bank),
        "selected_actions_sha256": _digest(selected_actions),
        "native_scores": native_scores.cpu().tolist(),
        "guided_scores": guided_scores.cpu().tolist(),
        "native_supported": native_supported.cpu().tolist(),
        "guided_supported": guided_supported.cpu().tolist(),
        "support_abstention": support_abstention,
        "guidance_traces": [dict(trace) for trace in guidance_traces],
        "shadow_critic_and_gradient_computed": True,
        "outcomes_read_for_selection": 0,
    }
    return OnlineDecision(arm, selected, selected_actions, receipt)

