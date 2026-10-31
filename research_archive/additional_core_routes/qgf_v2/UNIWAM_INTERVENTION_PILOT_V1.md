# UniWAM Training-Only Random Intervention Pilot V1

## Admission

The N4 numeric gate passed at fixed engineering scene 1000100000 with exact
candidate0/native/replay and selected2 replay equality, valid history/RNG
restoration and positive candidate diversity. Its complete report and raw arrays
are retained. Exit signal 11 after the probe returned remains a separate runtime
fault, not a clean-exit PASS. Original model/source/weights remain unchanged.

## Frozen Episodes

Task lift_pot/demo_clean only. Exactly four accepted expert-feasible episodes;
no task screening, outcome-based replacement or class-balancing extension.
Episode 0/1/2/3 use the first expert-feasible scene in the following half-open
training-only windows, respectively:

| Episode | Environment window | Independent selection seed |
| --- | --- | --- |
| 0 | [202637100,202637120) | 202637501 |
| 1 | [202637200,202637220) | 202637502 |
| 2 | [202637300,202637320) | 202637503 |
| 3 | [202637400,202637420) | 202637504 |

Keep every feasibility attempt and failure with its reason. Accept by the
official expert plan_success/check_success check only, before policy execution.
Unknown exceptions stop the run rather than silently skip scenes. Exhausting a
window stops the pilot. No completed policy episode can be replaced or rerun.
All windows, selection seeds and engineering seeds are excluded from validation
and formal sets. Select unseen instructions with the official generator, with
their text and RNG state recorded before any policy action.

## Actions, Labels And RNG Isolation

- Preserve the official 14D qpos action, chunk16/replan16 (early termination
  only by official success or step limit400), three-camera preprocessing,
  history_flow, four denoise steps, history noise0.02 and future-video1.0.
- Every boundary generates exactly four native candidates from one observation
  and identical policy memory: candidate0 uses the captured native RNG stream;
  alternatives use fixed seeds11000/12000/13000, as in the admitted N4 probe.
  Selection is uniform from an independent np.random.default_rng per episode.
- Restore selected post-inference policy memory, including caches/history.
  To prevent candidate reseeding from changing simulator/planner randomness,
  restore caller Python/NumPy/Torch CPU/CUDA RNG to candidate0's post-inference
  stream before executing any environment action, for every selected index.
  Thus a candidate0 decision matches a single native call's state and RNG;
  hypothetical candidates never leak their reseeding into the simulator.
  This execution-boundary composition is explicitly introduced here, after the
  zero-action gate, not retrospectively attributed to that gate. Audit selected
  memory and candidate0 caller RNG separately before every real execution.
- In the pilot only, replay the selected candidate from the original snapshot
  as a deterministic audit, and compare action and post-state hashes; replay
  does not execute actions or receive labels. First boundary per episode also
  replays candidate0. Include all audit-request cost in wall/GPU time.
- Execute the selected chunk unchanged for up to16 actions. At each step,
  save the exact submitted qpos and actual returned simulator qpos feedback;
  update history with the official record_executed_qpos method.
- Actual step reward is float(env.eval_success), the official sparse success
  flag after that executed step. The finite-horizon target is the sum of these
  observed rewards in this executed chunk (discount1); it is not a predicted
  reward or expert reward. Unexecuted candidates have no labels. Save all step
  rewards, termination/truncation, actual execution lengths and R+1 boundary
  observations. No oracle enters action selection.

## Evidence And Gate

Save all candidate arrays/hashes/diversity, selection index and independent
selector RNG, executed commands/feedback/rewards, observations, policy/RNG
state hashes, latency, videos, config, source/runtime hashes and failures.
Pass requires four complete policy episodes, all finite [4,16,14] banks with
four different hashes and positive pairwise MAD, selected replay/commit error
<=1e-6, exact memory/caller-RNG restoration, R+1 observation continuity, valid
videos, and at least one success and one failure. A single class or scientific
audit failure freezes this task/config; do not change task/seeds/gates or expand.
Keep process-exit status separate from completed data and never erase failures.

## Budget

One model on one allocated idle A800, 8 CPUs, 45 GB RAM, sequential four episodes
to avoid the known50GB allocation's dual-model OOM. Warm native requests measured
1.17-1.20s; full baseline including setup/load was458s. Worst-case400 steps means
25 boundaries per episode, approximately6s native+audit work per boundary plus
simulation and startup. Expected15-30minutes; hard60minutes/1GPU-hour. All failed
attempt costs are retained. No second model is launched just to use idle GPUs.

Pilot PASS only admits a separately budgeted training dataset with at least6S6F.
Episode-disjoint OOF, at least3bootstrap seeds, fixed-last-step/episode-equal
action-aware versus same-target state-only and shuffle/permutation gates remain
mandatory before a selector or fresh matched online evaluation is admitted.
