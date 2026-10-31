"""Frozen population-level admission metrics for Progress-Pairwise QGF V1."""

from collections import defaultdict

import numpy as np


BOOTSTRAP_SEED = 202641501
BOOTSTRAP_DRAWS = 10000


def evaluate_horizon(rows, horizon):
    success_key = f"success_at_{horizon}"
    progress_key = f"progress_at_{horizon}"
    discordant = []
    family_ranges = defaultdict(list)
    for row in rows:
        branches = row["branches"]
        successes = [bool(branch[success_key]) for branch in branches]
        values = np.asarray([branch[progress_key]["value"] for branch in branches],
                            dtype=np.float64)
        if len(branches) != 8 or values.shape != (8,) or not np.isfinite(values).all():
            raise RuntimeError("Invalid N8 endpoint")
        if len(set(successes)) > 1:
            discordant.append(row["episode_id"])
        family_ranges[row["family"]].append(float(values.max() - values.min()))
    discordant_families = sorted({row["family"] for row in rows
                                  if row["episode_id"] in discordant})
    reports = {}
    passing = []
    for family_index, family in enumerate(sorted(family_ranges)):
        values = np.asarray(family_ranges[family], dtype=np.float64)
        rng = np.random.default_rng(BOOTSTRAP_SEED + horizon * 10 + family_index)
        sampled = values[rng.integers(0, len(values), size=(BOOTSTRAP_DRAWS, len(values)))]
        lower, upper = np.quantile(sampled.mean(axis=1), [0.025, 0.975])
        passed = bool(lower > 0.0)
        reports[family] = {
            "groups": len(values),
            "mean_candidate_range": float(values.mean()),
            "ci95": [float(lower), float(upper)],
            "passes": passed,
        }
        if passed:
            passing.append(family)
    return {
        "binary_discordant_groups": discordant,
        "binary_discordant_families": discordant_families,
        "binary_signal_pass": len(discordant) >= 4 and len(discordant_families) >= 2,
        "dense_family_reports": reports,
        "dense_passing_families": passing,
        "dense_signal_pass": len(passing) >= 2,
    }


def qualify(rows):
    complete = len(rows)
    horizon16 = evaluate_horizon(rows, 16)
    horizon32 = evaluate_horizon(rows, 32)
    signal = complete >= 12 and any((horizon16["binary_signal_pass"],
                                     horizon16["dense_signal_pass"],
                                     horizon32["binary_signal_pass"],
                                     horizon32["dense_signal_pass"]))
    return {
        "status": ("PROGRESS_PAIRWISE_ACTION_VALUE_SIGNAL_ADMIT"
                   if signal else "NO_PROGRESS_PAIRWISE_ACTION_VALUE_SIGNAL"),
        "complete_groups": complete,
        "horizon16": horizon16,
        "horizon32": horizon32,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_draws": BOOTSTRAP_DRAWS,
    }
