"""Summarize fixed-final-step QGF-v4 intervention critic controls."""

import hashlib
import json
from pathlib import Path
import statistics


SEEDS = [202623001, 202623002, 202623003]
KINDS = ["action", "state_only", "action_shuffle"]


def main():
    suite = Path(__file__).resolve().parent / "v4_critic_v1"
    rows = []
    for kind in KINDS:
        for seed in SEEDS:
            name = f"{kind}_seed{seed}"
            directory = suite / "training" / name
            if not (directory / "COMPLETE").exists():
                raise ValueError(f"missing fixed run: {name}")
            final = json.loads((directory / "metrics.jsonl").read_text().splitlines()[-1])
            if final["step"] != 10000:
                raise ValueError(f"non-final checkpoint: {name}")
            rows.append({"kind": kind, "seed": seed, "name": name, "final": final,
                "checkpoint_sha256": hashlib.sha256((directory / "latest.pt").read_bytes()).hexdigest()})

    by_kind = {kind: {row["seed"]: row for row in rows if row["kind"] == kind} for kind in KINDS}
    comparisons = []
    wins = 0
    for seed in SEEDS:
        action = by_kind["action"][seed]["final"]["episode_equal_undiscounted_success_mse"]
        state = by_kind["state_only"][seed]["final"]["episode_equal_undiscounted_success_mse"]
        shuffled = by_kind["action_shuffle"][seed]["final"]["episode_equal_undiscounted_success_mse"]
        win = action < state and action < shuffled
        wins += int(win)
        comparisons.append({"seed": seed, "action_mse": action, "state_only_mse": state,
            "action_shuffle_mse": shuffled, "action_minus_state": action - state,
            "action_minus_shuffle": action - shuffled, "beats_both": win})
    aggregate = {kind: statistics.mean(by_kind[kind][seed]["final"]["episode_equal_undiscounted_success_mse"]
        for seed in SEEDS) for kind in KINDS}
    aggregate_positive = aggregate["action"] < aggregate["state_only"] and aggregate["action"] < aggregate["action_shuffle"]
    admit = wins >= 2 and aggregate_positive
    status = "ADMIT_FRESH_MATCHED_ONLINE" if admit else "NO_STABLE_ACTION_VALUE_EVIDENCE"
    result = {"schema": "qgf_v4_intervention_critic_conclusion_v1", "status": status,
        "admits_matched_online": admit, "wins_over_both_controls": wins,
        "aggregate_validation_mse": aggregate, "comparisons": comparisons, "runs": rows,
        "warning": "This qualification diagnostic is not an online robot success-rate result."}
    (suite / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# QGF v4 Intervention Critic Conclusion", "", f"Status: {status}", "",
        f"Action-aware beats both controls in {wins}/3 frozen bootstrap seeds.",
        f"Aggregate MSE: action={aggregate['action']:.8g}, state-only={aggregate['state_only']:.8g}, action-shuffle={aggregate['action_shuffle']:.8g}.", "",
        "| Seed | Action | State-only | Action-shuffle | Beats both |", "| --- | ---: | ---: | ---: | --- |"]
    for row in comparisons:
        lines.append(f"| {row['seed']} | {row['action_mse']:.8g} | {row['state_only_mse']:.8g} | {row['action_shuffle_mse']:.8g} | {row['beats_both']} |")
    lines += ["", "This fixed held-out diagnostic only determines whether to run fresh matched online robot evaluation."]
    (suite / "METHOD_CONCLUSION.md").write_text("\n".join(lines) + "\n")
    (suite / "COMPLETE").touch()
    print(json.dumps({"status": status, "wins": wins, "aggregate": aggregate}))


if __name__ == "__main__":
    main()
