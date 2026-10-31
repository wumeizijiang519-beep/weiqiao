# QGF v2 development branch

## Result-first supervision and separate small-data diagnostic

User2026-10-24 explicitly prioritized producing a method conclusion and updated
the30minute automation. SMALL_DATA_CV_V1.md is the new independent diagnostic
protocol using retained60=56S4F, four45/15 folds (42S3F/14S1F), CVseed202621500.
The original standard60 route remains STOP_INSUFFICIENT_CLASSES: no old gate is
silently relaxed, and no independent online/formal success claim follows CV.

Train TD099, calibrated1 and same-target state-only at seeds0/1/2 across4folds,
fixed10000steps (36runs), final-step reporting not validation-selected best.
First oneGPU pilot measures timing; only if remaining conservative estimate<=8
GPU-hours dispatch35 further runs on4 idle allocated GPUs, hard3hour/12GPU-hour
parallel-stage cap. Write METHOD_CONCLUSION.md, including negative/inconclusive
results and limitations from only4 independent failures. No new blind sampling.
Fresh10-seed online feasibility remains a separately frozen next stage.

## Probe result and matched-reference full smoke

Zero-action parity probe saved reproducible inputs/raw arrays. Candidate commit0,
commit1, reset-repeat and each native service's repeat tests all had max error0.
Candidate0 and fresh native also matched exactly; both differed from existing
native reference by0.0029296875. Underlying runtime difference remains unproven.
Do not claim a repaired legacy service or weaken the strict1e-6 tolerance.
MATCHED_REFERENCE_RETRY3.md admits one full engineering episode using a fresh
original-entrypoint native reference paired with the candidate service on the
same allocated node. Old reference results cannot be mixed into this pairing.
Scene202619100/selection seed202619001 remain excluded from training/formal.
Three assigned GPUs,45minutes/2.25GPU-hour cap. Bulk/critic launch still gated.

## Candidate0 mismatch diagnostic in progress

Retry2 passed first-scene feasibility but stopped before executing policy actions:
candidate0 vs existing native reference max absolute difference0.00292969,
62/160 components outside the frozen1e-6 tolerance. Retain its FAILED evidence;
no candidate/native or robot smoke admission follows. Tolerance is unchanged.

PARITY_PROBE_V1.md freezes a20minute,zero-executed-action diagnostic on the same
engineering scene202619100. Save a replayable initial observation and compare
candidate/commit0, reset/repeat, candidate1/commit1, fresh native repeated act,
existing native repeated act and all cross-service outputs. Three new assigned
GPU tasks,1GPU-hour cap (1.34 including existing native reference conservatively).
PARITY_PROBE_COMPLETE is diagnostic evidence only, never QGF gate admission.

## Exploration smoke feasibility retry

Original engineering seed202619000 failed official expert feasibility due to an
unstable018_microphone object; zero policy episodes/actions executed. Evidence
and original exact-seed contract remain preserved. EXPLORATION_SMOKE_RETRY2.md
preregisters one new named engineering run: first official expert-feasible scene
in [202619100,202619120), at most20 feasibility checks, one executed episode,
45minute cap. Exclude the full engineering window from subsequent datasets.
No policy-outcome filtering, no checkpoint/action/success change, no relaxation
of candidate/native or selected/commit parity. Bulk collection remains blocked.

## User-authorized route redetermination

After the60-episode admission stop, the user instructed us to continue and
redetermine the route. `EXPLORATION_REPLAN_V1.md` admits only one independent
training-behavior safety/timing smoke: random selection among four native WAM
proposals at one current observation, exact engineering seed202619000. No
injected action noise, changed success/deadline, oracle or fabricated failure.
First-observation candidate0/native parity and every selected/committed action
must match at absolute tolerance1e-6. Preserve R+1 transition audits.
Two allocated GPU tasks,45minute total cap;1.5GPU-hours for new tasks and at
most2.25GPU-hours conservatively including the already-loaded native reference.
This does NOT authorize bulk collection yet or relax the stopped60 gate. Smoke
must pass before using measured timing to preregister a new bounded dataset.

## Completed60: data route stopped, no training admitted

Both approved extension shards completed10success/0failure and passed their
transition audits. Combined data are56success/4failure across60 retained episodes.
handoff60_state.json is STOP_INSUFFICIENT_CLASSES. Combined audit SHA256:
bde57dcd15dddfd07d63fe5209a3faded3e8b7f1e63ddb217a84718e33e74483.
There is no dataset60 export/frozen split and no training60 directory. Do not
restart this collector, lower the six-failure gate, repurpose old evaluation
failures as training data, or launch critics on an unadmitted dataset. All60
episodes and negative evidence remain retained. Further collection on this
route needs a separate explicit authorization; the approved20 cap is exhausted.
Continue CPU release/adapter audits and reward-free method engineering only
until another preregistered, admissible route is available. This is a data-class
limitation, not evidence that v2 succeeds or fails online.

## Executable CVPR evidence plan

`CVPR_EXECUTION_PLAN_V2.md` consolidates the authorized method-development
sequence and reporting limits. Existing fixed collection/training contracts
remain authoritative. The initial method is frozen-WAM action proposal plus
offline RL critic learning and conservative inference-time policy improvement,
not end-to-end WAM reinforcement-learning fine-tuning.

`online_critic.py` now provides three-checkpoint loading with distinct seed0/1/2,
identical objective/manifest/scaler checks, identical current-frame/offline RGB
encoding, finite4x10x16 scoring and relative selector telemetry. All27 software
tests pass, including synthetic checkpoint/direct scoring parity. This is a
scoring component only: no real trained-critic parity, robot integration, new
safety smoke or online improvement is claimed. Deployment remains gated.

## Authorized extension superseding the fixed40 collection stop

The original40 finished36success/4failure and stopped without dataset export or
training. The user explicitly approved at most20 additional accepted episodes.
`EXTENSION20_APPROVED.md` and `extension20_proposal_v1.json` freeze the two new
candidate windows, total60 cap,48/12 split seed202616500 and unchanged class gate.
This is disclosed outcome-informed development collection, not a formal result.
No further collection is authorized if60 still has fewer than6failures.
Original40 evidence remains intact. All earlier no-expansion statements below
describe the original40 authorization; only this explicit20-episode exception
supersedes them. All other scientific and safety constraints remain unchanged.

Status: selector/return-target prototype. No trained v2 critic or online gain yet.
This branch is authorized method development; legacy results remain frozen.

## 2026-10-23 implementation progress

- `learning.py` now implements episode-equal smooth-L1 MC/TD calibration and
  measured same-state paired ranking loss. Eleven CPU software tests pass in the
  cluster's existing UNITAS environment, including detached targets and tie labels.
  Training integration, new data, and independent validation remain outstanding.
- Full episodes must be sampled uniformly before row subsampling; balancing only
  whichever episodes happen to appear in a uniform-row minibatch is insufficient.
- Source audit found UNITAS transaction restoration of history, converter state,
  replan count, Python/NumPy/Torch RNG, CUDA RNG and sampling-generator RNG on an
  exception. Full environment/renderer/robot/task-state restoration remains unproven.
  No same-state branch labels have been collected or used yet.
- Completed additional randomized gates: blocks_ranking_rgb 5/5,
  dump_bin_bigbin 5/5, blocks_ranking_size 5/5, stack_bowls_three 4/5.
  These are screening results, not QGF results or new collection authorization.
- Installed SAPIEN 3.0.0b1 exposes scene `pack_poses/unpack_poses` and CPU
  physics `pack/unpack`. A single free-falling rigid-body CPU smoke reproduced
  all 20 post-restore pose samples with maximum error 0.0. This only establishes
  a usable low-level primitive. Articulation drive targets, robot controller
  caches, task flags/counters, rendering, RNG and model-memory parity still need
  end-to-end validation before any branch labels are valid.
- Actual-task retry2 explicitly restores 38 drive targets/velocities and robot
  scalar/array fields. Immediate joint restore error and static rerender error
  are both zero, but the two-action replay still differs (joint max 7.114e-5,
  RGB max 68). No gate relaxation or branch admission follows this result.
- Retry3 separately tests documented planner sampling reset on both replay arms
  and records generated path differences. This is an explicit execution-contract
  diagnostic; any use in data collection also requires baseline parity under the
  changed reset contract. It is not claimed to reproduce an opaque planner cache.
- Retry3 retained a nonzero replay error (joint max 2.791e-5), with right-arm
  planned-path differences 8.475e-5 and 4.679e-5. Retry4 isolates physics by
  replaying recorded joint plans; it is a diagnostic only and cannot admit labels.
- Retry4 recorded-plan diagnostic reduces joint error to 3.725e-9. RGB remains
  nonidentical (MAE0.493/255, max75, fraction with abs error>10 is 0.002449).
  Exact-RGB acceptance is unchanged. Physical/control restoration is greatly
  improved for this short trace; full branch admission remains false. Stop
  repeating minimal smokes and prioritize standard-data MC/TD validation while
  longer-horizon/planner/renderer restoration is investigated separately.

## Parallel standard-data route

User-authorized v2 development continues without making snapshot parity a
dependency for ordinary trajectory data. `standard_collection_prereg_v1.json`
freezes fresh stack_bowls_three/demo_randomized collection: engineering smoke
seed202615000 excluded, four independent ten-episode candidate sequences starting
202615100/200/300/400, total cap40, split seed202615500. No old dataset is expanded.
Use the existing audited collector with official execution and success predicate.
Only after smoke validation launch four shards, with a 180-minute per-shard cap.
Estimate 100 minutes wall and 13.34 GPU-hours across four simulators/four servers.
All outcomes are retained, and fewer than six successes or six failures stops
training. The engineering seed, all gate seeds, and other partitions are excluded.
Train/validation split must have at least four/two failures respectively and both
classes; no outcome-dependent collection extension is permitted.

This data admits only standard TD/MC calibration, representation diagnostics and
ensemble training; same-state preference loss remains disabled pending reliable
branch restoration. Restore diagnostics and the standard-data smoke run in
parallel on separate allocated simulator slots and model servers.

### Complete transition contract required before collection

Audit identified that the original replan-level collector stores only R current
observations and full predicted chunks; it omits the final next observation and
explicit actual execution lengths. This suffices for previous trajectory-level
engineering checks but not the new TD/finite-horizon training contract.

Use `qgf_v2/trajectory_collector.py`, `run_standard_collection.sh` and
`validate_transitions.py` for the new dataset. Observations are R+1, chunks R,
actual lengths and per-step sparse rewards explicit, finite-horizon task terminal
separate from interruption. Store actual accepted feasibility seed in the NPZ
and cross-check it against the official episode result; never derive accepted
seeds by adding an index when expert-feasibility skips can occur. Fourteen CPU
software tests now pass. Legacy artifacts remain unchanged.

The new-schema smoke uses the same excluded engineering seed202615000 and an
independent free simulator/server pair in `qgf_v2/runs/standard_smoke_seed202615000_v2`.
The earlier engineering smoke can complete but cannot admit the new TD contract.
Only the new-schema smoke's `audit.json` with valid=true admits the fixed40
standard collection; no inference is made from a process-completion marker alone.

The new-schema smoke passed: seed202615000, success at461 action steps,
47 chunks and48 observations, finite values and official-result correspondence
verified. NPZ SHA2569002893e23a6622112a78202cb6709bf59c87a11bb6551f076fa4ae8c885fc11.
Measured launch-to-audit time571seconds includes loading and teardown.
Fixed40 collection started in job1581551 step243 with four Slurm tasks bound to
distinct GPUs0/1/2/3 and four isolated servers. CPU allocation is4 per task,
16 total. The first attempted64-CPU step was rejected before any episode;
failure log is retained, and seeds/episode budget unchanged.
Each shard is bounded to its100-candidate scene window and records every expert
feasibility attempt. A window exhaustion is a stop condition, never permission
to enter another shard's range. Validate actual accepted seeds globally before
freezing the dataset. No training or v2 online result exists yet.

### CPU preparation while collection runs

`features.py` and `prepare_dataset.py` prepare a transparent fixed-feature
baseline: 16x16 RGB patch mean/std on head/left/right96px frames (648D), raw
38D joints,14D TCP and remaining task time (701D total). These are explicitly
not WAM hidden tensors. Fit state/action scaling only on train episodes with
equal total weight per episode, keeping full predicted10x16 chunks as Q inputs.
Do not encode actual executed length or terminal labels into Q inputs.

`feature_smoke_v1.json` passes on all48 observations of the engineering episode:
batch versus current-frame feature maximum error0.0, finite outputs. Eighteen CPU
software tests pass including split class extremes, leakage separation, camera
order and episode-equal scaling. No real dataset export/training is started early.

After all40 complete, run `prepare_dataset.py --root ROOT --output NEW_DIRECTORY`.
It revalidates actual accepted seeds/arrays, checks old evaluation and smoke seed
exclusions, then freezes32/8 train/validation. Validation failure count is nearest
20% of retained failures, clipped to at least2 and at most7 while reserving at
least4 train failures; remaining slots are successes. Fewer than6 successes or6
failures stops the route. The output manifest and training-only scaler are
persistent and refuse overwrite. Same-state ranking supervision remains disabled.

### Frozen standard-data training ablations

`training_prereg_v1.json` fixes the direct701D-feature critic before dataset
freeze: two Q heads plus a value head, width256,10000 steps, batch32, Adam3e-4,
expectile0.7 and target rate0.005. Compare TD gamma0.99, TD gamma1 and
MC-calibrated TD gamma1/MCweight0.5, each seeds0/1/2. Add the calibrated
state-only control at the same three seeds (12 runs total). All conditions use
the same features and episode sampler; this is a matched-objective reference,
not the old Tau0 architecture. No token autoencoder is used in this fixed-feature
ablation. Full proposed action chunks remain Q inputs; execution lengths only
enter reward/bootstrapping targets, avoiding terminal-length input leakage.

`train_critic.py` prepares class-preserving episode bootstrap sampling, persistent
latest/best checkpoints and validation every500 steps. Select each fixed run by
episode-equal validation MC MSE; this is not evidence of causal action ranking.
The state-only and action-shuffle controls measure shortcut risk; only matched
online validation can establish net efficacy. Training admission is rechecked
inside the trainer (32/8 unique disjoint episodes, train>=4/validation>=2 failures,
both classes, feature/scaler SHA). Four new CPU mathematical/gradient tests pass
(22 software tests total); no real training is launched while data are partial.

After admission, measure first1000 steps as part of the first full run to budget
all12 conditions; record total GPU/wall cost before launching the rest. Use
`run_critic.sh`, which redirects driver/Triton/Matplotlib caches into pqr because
/public/home is nearly full. Same-state pairwise loss remains disabled.

### Bounded automatic handoff

`watch_standard40.py` monitors only the four fixed shards up to their original
180-minute collection deadline. After all four audited completions, it freezes
the combined audit, runs CPU dataset preparation, and stops on any class/seed/
array failure. Only on admission may it dispatch one10000-step TDgamma0.99 seed0
training run through Slurm job1581551, after freshly checking that the allocation
is RUNNING and belongs to the current user. That first run has a hard3600-second
cap (one GPU-hour); remaining11 runs stay unlaunched pending measured timing.
`handoff_state.json` and separate logs retain every transition. No GPU work is
scheduled while the data are partial. System watcher uses Python3.6-compatible
subprocess arguments; data export/training use the existing modern UNITAS Python.

## Questions supported by the source audit

- IQL uses per-action-step gamma 0.99 by default. Terminal success at 1000
  steps contributes only 0.000043 at episode start, before approximation error.
  Audit effective configs and measured Q scales before attributing any result.
- Current diagnostics measure across-episode AUC, not same-state action ranking.
  State recognition can succeed without useful action dependence.
- Inference queries generated alternatives beyond logged behavior actions.
  Existing twin-Q heads alone are not independent uncertainty estimates.
- Final training validation loss is measured only at the end of each run.
  Add periodic held-out checks and select using ranking/calibration diagnostics.

## Proposed method

1. Compare original TD training with finite-horizon success MC calibration plus
   TD regularization. Include remaining task time in the state for that objective.
   Keep true task deadlines distinct from infrastructure interruptions. Use only
   observed rewards; synthetic corrupted actions do not receive failure labels.
2. Train at least three independently initialized, episode-bootstrap critics.
   Weight episodes equally so long failures do not dominate via chunk count.
   Preserve natural validation prevalence; report per-class calibration.
3. At the same observation, score candidate advantages relative to candidate0.
   Switch only when mean advantage minus an ensemble-disagreement penalty exceeds
   the validation-frozen threshold and the action is within training-scaled trust
   distance. Log every decision, including abstentions and raw scores.
   This dispersion bound is heuristic until empirically calibrated.
4. Test action dependence with shuffled actions and state-only baselines. These
   diagnostics alone do not establish causal ranking. Add a bounded training-only
   same-state branching dataset if official simulator/RNG snapshots are validated.
   Branches execute one candidate then the unchanged continuation policy; retain
   all outcomes, reset model memory and RNG, and budget matched continuations.
   No environment branching or reward access is allowed at deployment.
5. Where a backbone exposes reliable action-conditioned future predictions, test
   a future-state value head as a later ablation. Establish prediction accuracy and
   online/offline feature consistency first; do not invent a rollout interface.

## Evaluation and stopping

Use fresh development data and episode-disjoint train/validation/test splits.
Existing old formal outcomes cannot select v2 parameters. Previously inspected
datasets are engineering evidence only. Freeze tasks and caps before new runs.

Compare base N1, candidate0 N4, random N4, original QGF N4, calibrated critic N4,
and gated ensemble N4 on identical held-out validation seeds. Report all methods,
including negative results, switching rate, rescue/regression counts, calibration,
action sensitivity, uncertainty, diversity, latency and GPU hours. Validation
selection across multiple tasks must be disclosed; final test tasks/seeds remain
sealed. Include failures even if validation rejects a method.

Offline gates: action-contract tests, episode leakage audit, finite targets,
held-out action ranking and state-only ablation. Then online one-episode safety
smoke; then bounded matched validation. Estimate rollout/GPU cost from measured
latency before collection or any stage above two hours. No new GPU experiment is
launched by this document. The current selector tests are synthetic software
checks and do not measure robotic success or statistical coverage.
