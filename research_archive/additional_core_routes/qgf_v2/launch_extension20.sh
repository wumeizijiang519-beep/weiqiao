#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
HOST="${1:?freshly discovered gpu1 host required}"
mkdir "$STAGE/extension20_launch.lock"
test ! -e "$STAGE/STANDARD60_EXTENSION_SRUN_PID"
test ! -e "$STAGE/runs/standard_train10_seed202616100"
test ! -e "$STAGE/runs/standard_train10_seed202616200"
nohup srun --jobid=1581551 --overlap --nodes=1 --ntasks=2 --gpus-per-task=1 --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=0 bash "$STAGE/dispatch_extension20.sh" "$HOST" >"$STAGE/extension20_srun.log" 2>&1 < /dev/null &
echo "$!" >"$STAGE/STANDARD60_EXTENSION_SRUN_PID"
nohup /usr/bin/python3 -u "$STAGE/watch_standard40.py" --root "$ROOT" --job 1581551 --extension20-approved >"$STAGE/handoff60_watcher.log" 2>&1 < /dev/null &
echo "$!" >"$STAGE/HANDOFF60_WATCHER_PID"
sha256sum "$STAGE"/{dispatch_extension20.sh,launch_extension20.sh,prepare_dataset.py,train_critic.py,watch_standard40.py,extension20_proposal_v1.json,EXTENSION20_APPROVED.md,PROTOCOL.md} >"$STAGE/extension20_checksums.sha256"
