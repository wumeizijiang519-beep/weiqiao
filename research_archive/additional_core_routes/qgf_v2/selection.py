"""Experimental baseline-relative selector; no environment rewards at inference."""
from dataclasses import dataclass
import math
import statistics


@dataclass(frozen=True)
class SelectionConfig:
    uncertainty_weight: float = 2.0
    min_advantage: float = 0.0
    max_normalized_rms: float = 1.0

    def __post_init__(self):
        values = (self.uncertainty_weight, self.min_advantage, self.max_normalized_rms)
        if not all(math.isfinite(x) and x >= 0 for x in values):
            raise ValueError("selector thresholds must be finite and nonnegative")


def select_candidate(ensemble_q, candidates, action_scale, config=SelectionConfig()):
    """Score paired Q differences, using independently trained ensemble members.

    Q has shape [ensemble, candidate], actions [candidate, horizon, dimension].
    Scale must come from training data or the declared action normalization.
    Ensemble dispersion is a heuristic, not a calibrated confidence interval.
    """
    count = len(candidates)
    if count < 1 or len(ensemble_q) < 3:
        raise ValueError("need candidates and at least three independent critics")
    width = len(action_scale)
    horizon = len(candidates[0])
    if not width or not horizon or any(not math.isfinite(s) or s <= 0 for s in action_scale):
        raise ValueError("invalid horizon or action scales")
    for chunk in candidates:
        if len(chunk) != horizon or any(len(a) != width for a in chunk):
            raise ValueError("candidate action contract mismatch")
    if any(len(q) != count for q in ensemble_q):
        raise ValueError("Q candidate count mismatch")
    if not all(math.isfinite(q[0]) for q in ensemble_q) or not all(
        math.isfinite(x) for a in candidates[0] for x in a
    ):
        raise ValueError("baseline candidate must be finite")
    rows = []
    selected, best = 0, config.min_advantage
    for index, chunk in enumerate(candidates):
        finite = all(math.isfinite(x) for a in chunk for x in a) and all(
            math.isfinite(q[index]) for q in ensemble_q
        )
        if not finite:
            rows.append({"index": index, "eligible": False, "reason": "nonfinite"})
            continue
        rms = math.sqrt(sum(
            ((chunk[t][d] - candidates[0][t][d]) / action_scale[d]) ** 2
            for t in range(horizon) for d in range(width)
        ) / (horizon * width))
        differences = [q[index] - q[0] for q in ensemble_q]
        mean = statistics.mean(differences)
        spread = statistics.stdev(differences)
        score = mean - config.uncertainty_weight * spread
        eligible = rms <= config.max_normalized_rms
        rows.append({"index": index, "eligible": eligible, "mean_advantage": mean,
                     "advantage_std": spread, "score": score, "normalized_rms": rms})
        if eligible and score > best:
            selected, best = index, score
    return {"selected_index": selected, "switched": selected != 0,
            "candidates": rows}


def finite_horizon_returns(rewards, durations, *, gamma_per_step=1.0):
    """Observed chunk returns, for fully observed task-horizon episodes only.

    Rewards must already be discounted within each executed chunk. Success and
    official task deadline end the objective; interrupted records are excluded.
    These are behavior-policy MC targets, not optimal-Q or counterfactual labels.
    """
    if len(rewards) != len(durations) or not rewards:
        raise ValueError("need aligned nonempty rewards and durations")
    if not math.isfinite(gamma_per_step) or not 0 < gamma_per_step <= 1:
        raise ValueError("gamma must be in (0,1]")
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in durations):
        raise ValueError("durations must be positive integers")
    if not all(math.isfinite(r) for r in rewards):
        raise ValueError("rewards must be finite")
    result, value = [], 0.0
    for reward, duration in zip(reversed(rewards), reversed(durations)):
        value = reward + gamma_per_step ** duration * value
        result.append(value)
    return list(reversed(result))
