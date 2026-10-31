"""Run QGF-v5 folds, controls and seeds across four allocated workers."""

import json
import os
from pathlib import Path
import subprocess


SEEDS = [202624001, 202624002, 202624003]
KINDS = ["action", "state_only", "selected_permutation"]


def conditions():
    return [(fold, kind, seed) for fold in range(4) for kind in KINDS for seed in SEEDS]


def main():
    stage = Path(__file__).resolve().parent
    suite = stage / "v5_candidate_centered_v1"
    rank = int(os.environ["SLURM_PROCID"])
    (suite / "logs").mkdir(exist_ok=True)
    (suite / "training").mkdir(exist_ok=True)
    for index, (fold, kind, seed) in enumerate(conditions()):
        if index % 4 != rank:
            continue
        name = f"fold{fold}_{kind}_seed{seed}"
        output = suite / "training" / name
        command = ["/public/wangsenbao221/pqr/qgf_mainstream_20261022/envs/unitas_retry6/bin/python",
                   str(stage / "train_v5_centered.py"), "--stage", str(stage), "--output", str(output),
                   "--fold", str(fold), "--seed", str(seed), "--kind", kind, "--steps", "10000"]
        try:
            with (suite / "logs" / f"{name}.log").open("x") as log:
                result = subprocess.run(["timeout", "1800", *command], stdout=log, stderr=subprocess.STDOUT)
            if result.returncode or not (output / "COMPLETE").exists():
                raise RuntimeError(f"{name} failed: {result.returncode}")
        except Exception as exc:
            (suite / f"FAILED_{name}.json").write_text(json.dumps({"error": repr(exc)}) + "\n")
            raise


if __name__ == "__main__":
    main()
