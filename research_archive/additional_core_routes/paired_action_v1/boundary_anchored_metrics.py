"""Metrics and group-level admission logic for boundary-anchored interventions."""

from collections import defaultdict

import numpy as np


def goal_fraction(env) -> float:
    base = env.env if hasattr(env, "env") else env
    goals = tuple(base.parsed_problem["goal_state"])
    if not goals:
        raise RuntimeError("Task has no registered goal predicates")
    values = [bool(base._eval_predicate(goal)) for goal in goals]
    return float(sum(values) / len(values))


def bootstrap_family_dense_gate(rows, *, seed=202641001, draws=10_000):
    by_family = defaultdict(list)
    for row in rows:
        values = np.asarray(row["final_goal_fractions"], dtype=np.float64)
        if values.shape != (4,) or not np.isfinite(values).all():
            raise ValueError("Every complete group needs four finite progress labels")
        by_family[row["family"]].append(float(values.max() - values.min()))

    rng = np.random.default_rng(seed)
    reports = {}
    passing = []
    for family in sorted(by_family):
        effects = np.asarray(by_family[family], dtype=np.float64)
        samples = effects[rng.integers(0, len(effects), size=(draws, len(effects)))]
        means = samples.mean(axis=1)
        lower, upper = np.quantile(means, [0.025, 0.975])
        reports[family] = {
            "groups": int(len(effects)),
            "mean_effect": float(effects.mean()),
            "ci95": [float(lower), float(upper)],
            "passes": bool(lower > 0.0),
        }
        if lower > 0.0:
            passing.append(family)
    return reports, passing


def qualify(rows):
    complete = [row for row in rows if row.get("status") == "PAIRED_GROUP_COMPLETE"]
    binary = [row for row in complete if len(set(row["successes"])) > 1]
    binary_families = sorted({row["family"] for row in binary})
    dense_reports, dense_families = bootstrap_family_dense_gate(complete) if complete else ({}, [])
    enough = len(complete) >= 12
    binary_pass = enough and len(binary) >= 4 and len(binary_families) >= 2
    dense_pass = enough and len(dense_families) >= 2
    return {
        "complete_groups": len(complete),
        "binary_discordant_groups": len(binary),
        "binary_discordant_families": binary_families,
        "dense_family_reports": dense_reports,
        "dense_passing_families": dense_families,
        "binary_signal_pass": binary_pass,
        "dense_critic_signal_pass": dense_pass,
        "status": ("PAIRED_BINARY_SIGNAL_PASS" if binary_pass else
                   "PAIRED_DENSE_CRITIC_SIGNAL_PASS" if dense_pass else
                   "NO_PAIRED_ACTION_VALUE_SIGNAL"),
    }
