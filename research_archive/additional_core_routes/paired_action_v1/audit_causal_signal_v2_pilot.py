#!/usr/bin/env python3
"""Fail-closed release audit for the non-repeating Causal Signal V2 pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report_path = args.run / "REPORT.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    errors = []
    if (report.get("entry_start"), report.get("entry_stop")) != (0, 1):
        errors.append("pilot slice is not [0,1)")
    if report.get("complete_groups") != 1 or len(report.get("results", [])) != 1:
        errors.append("pilot does not contain one complete group")
    else:
        row = report["results"][0]
        group = args.run / row["episode_id"]
        with np.load(group / "bank.npz", allow_pickle=False) as data:
            bank = np.asarray(data["candidates_native"])
        if bank.shape != (8, 32, 7) or not np.isfinite(bank).all():
            errors.append(f"invalid bank {bank.shape}")
        if len({hashlib.sha256(candidate.tobytes()).hexdigest() for candidate in bank}) != 8:
            errors.append("bank candidates are not unique")
        if sorted(row.get("branch_order", [])) != list(range(8)):
            errors.append("branch order is not a permutation of N8")
        if len(row.get("branches", [])) != 8:
            errors.append("not all eight branches completed")
        for candidate in range(8):
            branch = group / f"candidate_{candidate}"
            result = json.loads((branch / "result.json").read_text(encoding="utf-8"))
            with np.load(branch / "trajectory.npz", allow_pickle=False) as data:
                actions = np.asarray(data["actions"])
                states = np.asarray(data["sim_states"])
            if not 1 <= len(actions) <= 32 or states.shape[0] != len(actions):
                errors.append(f"candidate{candidate} invalid trajectory length")
            if not np.array_equal(actions, bank[candidate, : len(actions)]):
                errors.append(f"candidate{candidate} action commit mismatch")
            if result.get("commit_max_error") != 0.0:
                errors.append(f"candidate{candidate} nonzero commit error")
            if len(actions) < 32 and not (result.get("success") or result.get("environment_done")):
                errors.append(f"candidate{candidate} stopped before32 without terminal")
    output = {
        "status": "CAUSAL_SIGNAL_V2_PILOT_PASS" if not errors else "CAUSAL_SIGNAL_V2_PILOT_FAIL",
        "errors": errors,
        "pilot_report_sha256": sha256(report_path),
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        raise SystemExit(2)
    (args.run / "PILOT_RELEASED").write_text(output["status"] + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
