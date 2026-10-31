#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R=$ROOT/simplewam_visual_rl_v1
PHYSICAL_LANE=${1:?physical lane required}
test "$PHYSICAL_LANE" -ge 0 -a "$PHYSICAL_LANE" -lt 4
bash "$R/run_online_lane_v2_worker8.sh" "$PHYSICAL_LANE" &
P0=$!
bash "$R/run_online_lane_v2_worker8.sh" "$((PHYSICAL_LANE + 4))" &
P1=$!
wait "$P0"
wait "$P1"
