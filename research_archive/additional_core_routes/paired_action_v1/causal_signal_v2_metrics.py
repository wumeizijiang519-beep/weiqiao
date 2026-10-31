"""Frozen group-level admission logic for Causal Signal V2."""

from collections import defaultdict

import numpy as np


def goal_fraction(env) -> float:
    base = env.env if hasattr(env, "env") else env
    goals = tuple(base.parsed_problem["goal_state"])
    if not goals:
        raise RuntimeError("Task has no registered goal predicates")
    values = [bool(base._eval_predicate(goal)) for goal in goals]
    return float(sum(values) / len(values))


def bootstrap_family_dense_gate(rows, value_key, *, seed=202641101, draws=10_000):
    by_family = defaultdict(list)
    for row in rows:
        values = np.asarray(row[value_key], dtype=np.float64)
        if values.shape != (8,) or not np.isfinite(values).all():
            raise ValueError("Every complete group needs eight finite progress labels")
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


def qualify_horizon(rows, *, success_key, value_key):
    complete = [row for row in rows if row.get("status") == "PAIRED_GROUP_COMPLETE"]
    binary = [row for row in complete if len(set(row[success_key])) > 1]
    binary_families = sorted({row["family"] for row in binary})
    dense_reports, dense_families = bootstrap_family_dense_gate(complete, value_key) if complete else ({}, [])
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
        "status": ("BINARY_SIGNAL_PASS" if binary_pass else
                   "DENSE_CRITIC_SIGNAL_PASS" if dense_pass else
                   "NO_SIGNAL"),
    }


def qualify(rows):
    horizon16 = qualify_horizon(rows, success_key="successes_at_16",
                                value_key="goal_fractions_at_16")
    horizon32 = qualify_horizon(rows, success_key="successes",
                                value_key="final_goal_fractions")
    admitted = horizon16["status"] != "NO_SIGNAL" or horizon32["status"] != "NO_SIGNAL"
    return {
        "horizon16": horizon16,
        "horizon32": horizon32,
        "complete_groups": horizon32["complete_groups"],
        "status": "CAUSAL_SIGNAL_ADMIT" if admitted else "NO_EXTENDED_NATIVE_ACTION_VALUE_SIGNAL",
    }
