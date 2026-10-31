#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022/simplewam_visual_rl_v1
srun --jobid=1598338 --exclusive -N1 -n1 --gres=gpu:1 --cpus-per-task=4 --mem=45G \
  bash "$ROOT/run_final_critic_seed.sh" 202644201 >"$ROOT/final_critic_seed_202644201_srun.log" 2>&1 &
P0=$!
srun --jobid=1598338 --exclusive -N1 -n1 --gres=gpu:1 --cpus-per-task=4 --mem=45G \
  bash "$ROOT/run_final_critic_seed.sh" 202644202 >"$ROOT/final_critic_seed_202644202_srun.log" 2>&1 &
P1=$!
srun --jobid=1673999 --exclusive -N1 -n1 --gres=gpu:1 --cpus-per-task=4 --mem=45G \
  bash "$ROOT/run_final_critic_seed.sh" 202644203 >"$ROOT/final_critic_seed_202644203_srun.log" 2>&1 &
P2=$!
printf '%s\n' "$P0" "$P1" "$P2" >"$ROOT/final_critic_dispatch_v1.launchers"
wait "$P0" "$P1" "$P2"
printf '0\n' >"$ROOT/final_critic_dispatch_v1.exit_code"
