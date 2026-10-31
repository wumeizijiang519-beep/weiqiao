"""Run fixed QGF-v4 critic/control conditions across four GPU workers."""

import json
import os
from pathlib import Path
import subprocess


SEEDS = [202623001, 202623002, 202623003]
KINDS = ["action", "state_only", "action_shuffle"]


def conditions():
    return [{"kind": kind, "seed": seed, "name": f"{kind}_seed{seed}"} for kind in KINDS for seed in SEEDS]


def main():
    stage = Path(__file__).resolve().parent
    suite = stage / "v4_critic_v1"
    rank = int(os.environ["SLURM_PROCID"])
    for index, row in enumerate(conditions()):
        if index % 4 != rank:
            continue
        output = suite / "training" / row["name"]
        command = ["/public/wangsenbao221/pqr/qgf_mainstream_20261022/envs/unitas_retry6/bin/python",
            str(stage / "train_v4_critic.py"), "--data", str(suite / "data"), "--output", str(output),
            "--seed", str(row["seed"]), "--device", "cuda", "--steps", "10000"]
        if row["kind"] == "state_only": command.append("--state-only")
        if row["kind"] == "action_shuffle": command.append("--action-shuffle")
        try:
            with (suite / "logs" / (row["name"] + ".log")).open("x") as log:
                result = subprocess.run(["timeout", "1800", *command], stdout=log, stderr=subprocess.STDOUT)
            if result.returncode or not (output / "COMPLETE").exists():
                raise RuntimeError(f"{row['name']} failed: {result.returncode}")
        except Exception as exc:
            (suite / ("FAILED_" + row["name"] + ".json")).write_text(json.dumps({"error": repr(exc), "condition": row}) + "\n")
            raise


if __name__ == "__main__":
    main()

