# QGF v2: WAM + Offline RL Execution Plan

Status: active method development, not demonstrated online improvement.
Scope: frozen WAM action proposals plus learned offline RL critics and a
reward-free deployment selector. This is not end-to-end backbone RL fine-tuning.
Novelty and conference suitability remain hypotheses, not verified claims.

## Scientific hypothesis

A trajectory-success recognizer can obtain high cross-episode AUC while being
useless for choosing actions at one state. Per-step gamma0.99 also severely
attenuates delayed sparse rewards. Test whether finite-task-horizon MC/TD
calibration and action-dependent, baseline-relative conservative selection can
reduce regressions without destroying the base WAM's successful behavior.

Primary model: Q(s, action_chunk, remaining_time). Three independently initialized
episode-bootstrap critics, each with twin Q heads and a value head. The WAM is
frozen; IQL-style value/TD learning plus observed behavior-policy MC targets
provides the offline RL component. MC targets are not counterfactual optimal Q.

Deploy four candidates from one current observation/replan boundary. For i>0,
use ensemble mean[Qi-Q0] minus lambda*std[Qi-Q0], gated by a training-scaled
action-distance threshold; otherwise execute candidate0. Disagreement is a
heuristic, NOT a statistical confidence guarantee. No reward, outcome, replayed
episode or simulator state branch is available to the deployed selector.

## Stage A: finish admitted data and isolate failure mechanisms

1. Retain fixed40 (36S4F) and the user-approved additional20, without selection.
   Extension windows, total cap60,180minute timeout and12GPU-hour maximum are
   frozen in EXTENSION20_APPROVED.md. No further expansion is authorized.
2. At combined>=6S6F, freeze48train/12validation, seed202616500; require>=4/2
   train/validation failures and both classes. Audit official seeds, transitions,
   arrays, finite values, termination versus interruption and SHA before export.
   Otherwise stop with an informative insufficient-data result.
3. RGB patch/proprio/time features701D are a transparent engineering reference,
   NOT WAM latent features. State/action scaling uses training episodes only.
4. Keep same-state branching disabled: strict restore parity has not passed.
   Never fabricate negative labels by corrupting actions. State-only and action
   shuffle are shortcut diagnostics, not evidence of causal action ranking.

## Stage B: fixed twelve-run RL comparison

All networks, sampling, steps and optimizer are held constant per training_prereg.

| Objective | Discount per action step | MC weight | Seeds | Role |
| --- | --- | --- | --- | --- |
| TD099 | .99 | 0 | 0/1/2 | Matched TD reference |
| TD1 | 1 | 0 | 0/1/2 | Isolate discount attenuation |
| Calibrated1 | 1 | .5 | 0/1/2 | Finite-horizon MC/TD method |
| State-only calibrated1 | 1 | .5 | 0/1/2 | Action-dependence control |

Train10000steps/run, batch32, width256, episode-equal bootstrap. Choose checkpoints
by held-out episode-equal MC MSE within each fixed objective; different discount
targets are NOT directly comparable measures of method quality. Report per-class
MSE, Q scale, TD error, action-shuffle delta, initial/late trajectory diagnostics,
and ensemble disagreement. Bootstrap/interval units are episodes, not chunks.

First TD099 seed0 has3600seconds/oneGPU-hour hard cap. Its measured first1000steps
determine all12-run GPU/wall estimates BEFORE launching the remaining11. Distribute
independent runs across freshly verified allocated idle GPUs; never replicate a
run just to occupy hardware. Training remains blocked until data admission.

## Stage C: online contract and bounded validation

Implement and test checkpoint loading, offline/current-frame feature parity,
normalization parity, finite4x10x16 proposals, distinct candidates, candidate0
sampling parity, and one state update per replan. Preserve WAM memory correctly.
online_critic.py is a reward-free scoring component, not yet a robot adapter.
Synthetic tests do not replace real-checkpoint/robot smoke.

Freeze a separate safety-smoke seed and fresh online validation scene windows
before launch, globally disjoint from collection, gates, historical and future
formal seeds. Use at most10 accepted validation seeds per method, same exact
accepted scene list, official success predicate and matched policy sampling.
Feasibility failures are recorded; never choose scenes by policy success.

Primary comparisons (all results retained):
1. Base N1 and candidate0 N4: parity check and inference-cost control.
2. Random N4: controls candidate generation/computation.
3. TD099 ensemble ungated N4: matched old-objective reference, NOT exact old Tau0.
4. Calibrated1 ensemble ungated N4: isolates objective change.
5. Calibrated1 conservative ensemble N4: primary v2 method.

Start with selector defaults lambda2, minimum advantage0, normalized RMS1.
Freeze these BEFORE online validation; do not sweep dozens of thresholds on ten
seeds. The ungated-versus-gated pair is the primary uncertainty/trust ablation.
Any later tuning requires a new named development protocol and independent
confirmation; report the search and negative methods. Training validation is for
checkpoint selection; online validation is for deployment-method selection.

Record per-replan candidate Q, selected index, relative margin, disagreement,
switch/abstention, diversity, action RMS, finite status and end-to-end latency.
No unverified candidate0 memory/sampling parity means no interpretable QGF gain.

## Stage D: independent confirmation and paper evidence

Only a method with validation rescues>regressions and valid safety/contract gates
may be frozen for new paired formal seeds. Formal outcomes cannot tune anything.
First30paired seeds are a disclosed feasibility result, NOT a sufficient broad
CVPR claim or guaranteed significant effect. Predefine final evaluation sample
size/budget before launch; target100paired scenes/task where resources permit.
Avoid outcome-dependent early stopping. Report formal null/negative results too.

Paper target: at least two architecture-distinct admitted WAMs, multiple tasks,
and both RoboTwin2.0 and genuine LIBERO-Plus where executable official adapters
exist. UNITAS is the first working route. Kairos/ImageWAM remain gated on actual
weights/dependencies/parity; do not count release-matrix promises as execution.
Do not mix clean/randomized tasks, backbones or old RoboSyn tables. Describe any
task/model selection on development data and limit the resulting claims.

Primary outcome: paired success-rate difference. Report Wilson success CIs,
paired bootstrap CI, exact McNemar, rescue/regression counts, task-level results,
failure categories, latency/GPU cost and training seed variation.30-100scenes can
still be underpowered for modest effects; a positive point estimate is not proof.

## Optional higher-risk innovation, not on the critical path

If official WAM APIs expose reliable action-conditioned future predictions,
compare current-state Q to predicted-future value with prediction-error and
online/offline parity audits. Freeze the predicted horizon and all budgets first.
Do not invent a rollout interface or replace measured branch labels with imagined
success. Native frozen semantic/latent features can replace RGB statistics only
in a separately named, leakage-free representation ablation. Neither extension
is assumed available or necessary for the first online v2 experiment.

## Compute and schedule

Current extension estimate110minutes from launch, cap180minutes. This is not an
online QGF result. After data admission, benchmark the pilot rather than promise
an unmeasured training time. Estimate each evaluation stage with observed seconds
per episode and number of methods/seeds; GPU-hours = episode wall hours times
occupied GPU count, including policy servers. Record concurrency and renderer/
CPU bottlenecks. More GPUs cannot eliminate missing failure labels or bad critics.

Use assigned resources only; never stop an unfamiliar process. Pause expansion
on single-class data, unreliable action/memory parity, nonfinite behavior or net
validation harm. Any run beyond1.5x measured expected latency without progress
gets a first-cause audit and a new named minimal retry, preserving all evidence.
