"""Frozen admission metrics for Support-Gradient QGF V1."""

from collections import defaultdict

import numpy as np


BOOTSTRAP_SEED = 202642501
BOOTSTRAP_DRAWS = 10000
GUIDED_INDEX = 7


def evaluate_horizon(rows, horizon):
    success_key = f"success_at_{horizon}"
    progress_key = f"progress_at_{horizon}"
    discordant = []
    family_deltas = defaultdict(lambda: {"candidate0": [], "random": []})
    for row in rows:
        branches = sorted(row["branches"], key=lambda item: item["candidate_index"])
        if [item["candidate_index"] for item in branches] != list(range(8)):
            raise RuntimeError("Invalid N8 indices")
        successes = [bool(branch[success_key]) for branch in branches]
        values = np.asarray(
            [branch[progress_key]["value"] for branch in branches], dtype=np.float64
        )
        if not np.isfinite(values).all():
            raise RuntimeError("Invalid N8 endpoint")
        if len(set(successes)) > 1:
            discordant.append(row["episode_id"])
        guided = float(values[GUIDED_INDEX])
        family_deltas[row["family"]]["candidate0"].append(guided - float(values[0]))
        family_deltas[row["family"]]["random"].append(guided - float(values.mean()))

    discordant_families = sorted(
        {row["family"] for row in rows if row["episode_id"] in discordant}
    )
    reports = {}
    passing = []
    for family_index, family in enumerate(sorted(family_deltas)):
        reports[family] = {}
        family_pass = True
        for control_index, control in enumerate(("candidate0", "random")):
            values = np.asarray(family_deltas[family][control], dtype=np.float64)
            rng = np.random.default_rng(
                BOOTSTRAP_SEED + horizon * 10 + family_index * 2 + control_index
            )
            sampled = values[
                rng.integers(0, len(values), size=(BOOTSTRAP_DRAWS, len(values)))
            ]
            lower, upper = np.quantile(sampled.mean(axis=1), [0.025, 0.975])
            passed = bool(lower > 0.0)
            reports[family][control] = {
                "groups": len(values),
                "mean_delta": float(values.mean()),
                "ci95": [float(lower), float(upper)],
                "passes": passed,
            }
            family_pass = family_pass and passed
        if family_pass:
            passing.append(family)
    return {
        "binary_discordant_groups": discordant,
        "binary_discordant_families": discordant_families,
        "binary_signal_pass": len(discordant) >= 4 and len(discordant_families) >= 2,
        "guided_index": GUIDED_INDEX,
        "dense_family_reports": reports,
        "dense_passing_families": passing,
        "dense_signal_pass": len(passing) >= 2,
    }


def qualify(rows):
    complete = len(rows)
    horizon16 = evaluate_horizon(rows, 16)
    horizon32 = evaluate_horizon(rows, 32)
    signal = complete >= 12 and any(
        (
            horizon16["binary_signal_pass"],
            horizon16["dense_signal_pass"],
            horizon32["binary_signal_pass"],
            horizon32["dense_signal_pass"],
        )
    )
    return {
        "status": (
            "SUPPORT_GRADIENT_ACTION_VALUE_SIGNAL_ADMIT"
            if signal
            else "NO_SUPPORT_GRADIENT_ACTION_VALUE_SIGNAL"
        ),
        "complete_groups": complete,
        "horizon16": horizon16,
        "horizon32": horizon32,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_draws": BOOTSTRAP_DRAWS,
    }
