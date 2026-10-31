#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
mkdir "$STAGE/small_data_cv_launch.lock"
test ! -e "$STAGE/small_data_cv_v1/orchestrator.lock"
sha256sum "$STAGE"/{prepare_small_data_cv.py,train_critic.py,cv_conditions.py,cv_worker.py,run_small_data_cv_suite.py,summarize_small_data_cv.py,SMALL_DATA_CV_V1.md} >"$STAGE/small_data_cv_code.sha256"
nohup /usr/bin/python3 -u "$STAGE/run_small_data_cv_suite.py" --root "$ROOT" --job 1581551 >"$STAGE/small_data_cv_orchestrator.log" 2>&1 < /dev/null &
echo "$!" >"$STAGE/SMALL_DATA_CV_ORCHESTRATOR_PID"
