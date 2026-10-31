"""Run three frozen seeds over the two owned, idle gpu22 devices."""

import json
from pathlib import Path
import subprocess
import time


ROOT = Path("/public/wangsenbao221/pqr/qgf_mainstream_20261022")
CODE = ROOT / "action_prefix_pretrain_v1"
RUN = CODE / "dispatch_v1_retry1"


def main():
    RUN.mkdir()
    pending = [202642301, 202642302, 202642303]
    active = {}
    result = 1
    try:
        while pending or active:
            for gpu, (seed, control) in list(active.items()):
                exit_path = control / "process_exit_code"
                if exit_path.exists():
                    if exit_path.read_text().strip() != "0":
                        raise RuntimeError(f"seed {seed} failed")
                    del active[gpu]
            for gpu in (0, 1):
                if pending and gpu not in active:
                    seed = pending.pop(0)
                    out = CODE / "checkpoints_retry1" / f"seed_{seed}"
                    control = ROOT / "runs" / f"qgf_action_prefix_seed_{seed}_retry1_process"
                    log = RUN / f"seed_{seed}.log"
                    remote = (f"nohup timeout 2460 bash {CODE}/run_owned_gpu22.sh {gpu} {seed} "
                              f"{out} {control} > {log} 2>&1 < /dev/null & echo $!")
                    launch = subprocess.run(["ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                                             "gpu22", remote], text=True, capture_output=True, timeout=20)
                    (RUN / f"seed_{seed}.launch.json").write_text(json.dumps({
                        "ssh_exit": launch.returncode, "stdout": launch.stdout,
                        "stderr": launch.stderr, "gpu": gpu, "job": 1598338}, indent=2))
                    if launch.returncode or not launch.stdout.strip().isdigit():
                        raise RuntimeError("owned launch not confirmed")
                    active[gpu] = (seed, control)
                    time.sleep(2)
                    if not control.exists():
                        raise RuntimeError("ownership/UUID/idle guard failed")
            if pending or active:
                time.sleep(10)
        (RUN / "ALL_SEEDS_COMPLETE").touch()
        result = 0
    finally:
        (RUN / "dispatcher_exit_code").write_text(str(result))


if __name__ == "__main__":
    main()

