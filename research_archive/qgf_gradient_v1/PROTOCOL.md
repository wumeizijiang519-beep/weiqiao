# WAM RL QGF CVPR Experiment Protocol

Version: 2026-10-26 v1. The user requested a feasible WAM + RL + QGF experiment
plan and execution, and explicitly corrected the name QGMF to QGF.

## Scope and authorization

The primary method is gradient guidance INSIDE the frozen WAM flow sampler.
Candidate reranking is a control, not a renamed QGF result. The actor remains
frozen; a separately trained TD/IQL action-value ensemble provides the gradient.
This is offline RL with test-time policy improvement, not actor fine-tuning,
PPO, supervised success classification, or end-to-end WAM RL training.

This is a new prospective method branch. All old stop decisions and results
remain immutable. No old single-class dataset is admitted for fitting; no old
formal scene is used for selecting a hyperparameter or reporting a fresh result.
No backbone search is authorized by this protocol. Reuse Simple-WAM because its
runtime and action interface are already reproducible, not because its earlier
success rate is favorable. Kairos is a conditional second-architecture extension
only after the new method passes its primary online gate.

Stage 0 is fully specified and is being executed now. Downstream stages are
conditional work packages, not permission to dispatch unimplemented collectors
or unregistered cohorts. They require their machine-readable manifest, tests,
cost forecast, and the preceding gate before launch, without changing this
scientific hypothesis. Any material scientific revision gets a new version
before new outcomes, never a retrospective threshold change.

## Research question

Can an execution-aligned RL value function and conservative, locally supported
Q-gradient improve a frozen WAM beyond both random native candidate selection
and unmodified QGF, at matched generation and critic compute?

Two candidate contributions, NOT established novelty claims:

1. Execution-aligned value learning: fit the actual committed prefix and its
   next observation/remaining time, rather than supervising an unexecuted
   32-step proposal with a 10-step transition or treating trajectory success
   recognition as same-state action discrimination.
2. Native-support and ensemble-consensus QGF: project the critic derivative
   into the span of differences among native candidates for the same
   observation; apply it only to the continuous executed prefix and only when
   all critic members agree on the local direction. Bound cumulative explicit
   correction and abstain outside a training-defined neighborhood.

The projection is geometric, not a proof of data support or safe improvement.
Ensemble agreement is not a confidence guarantee. Prefix alignment alone and
generic gradient clipping alone are not claimed novel. A literature comparison
and ablations must show a real distinction and benefit over existing QGF.

## Why this remains QGF

For the audited Simple-WAM descending-sigma scheduler:

    a_hat = a_sigma - sigma * v_theta(s, a_sigma, sigma)
    g_j = grad_prefix Q_j(s, a_hat_prefix, remaining_time)
    g_bar = mean_j g_j
    d = B B^T g_bar
    d = 0 if any dot(g_j, d) <= 0
    a_next = native_euler_step(v_theta, delta_sigma, a_sigma)
             + abs(delta_sigma) * beta * bounded(d)

B is an orthonormal basis of native normalized continuous-prefix differences
from candidate0. No actor Jacobian or backward pass through the WAM is used.
For the vanilla-QGF control use the unprojected derivative of the same critic,
with the same prefix, gradient cap, flow window and numerical precision.
The direct baseline is not deliberately handicapped by a mismatched horizon.
The separate horizon-mismatch ablation is explicitly labelled as such.

Current engineering settings: generation32, execute10, continuous coordinates6,
official binary gripper, sigma<=0.5, gradient norm<=1, explicit accumulated
normalized RMS correction<=0.05. Guidance acts before the official
denormalization/gripper conversion. Zero weight must preserve native output.
Zero *direct* suffix/gripper correction does not imply those final coordinates
cannot change indirectly through later coupled denoising steps; log both.
The correction budget is not a bound on final nonlinear displacement.

The official fast Simple-WAM mode freezes future video noise. Its current-frame
world-model encoder is available, but its generated future video is NOT an
action-conditioned counterfactual simulator. No hallucinated future reward or
unexecuted-candidate reward is used. A joint-video-mode ablation may be separately
costed later; no causal world-rollout claim follows the fast-mode experiments.

## Stage 0 integration gate

Run CPU tests of flow sign, no actor gradients, weight-zero equivalence, prefix
masking, rank-zero/ensemble disagreement abstention, correction budget, actual
execution length, terminal masking and detached IQL targets.

Then load the unchanged official Simple-WAM checkpoint on one verified idle
allocated A800. Reuse only the current observation from a retained transition
as an engineering input. Never read its reward to construct the toy critic.
No simulator instance, robot action, rollout or critic fit is performed.
Use synthetic linear critics solely to verify the implementation path.

Freeze source/checkpoint/config/SHA, raw normalized and native actions, every
flow-step trace, timing, peak memory, and process exit status. Gates in stage0.json:
native/w0/restored and guided repeat errors<=1e-6, finite32x7, official binary
gripper,10steps, nonzero local update with correct sign, unchanged source/input,
zero actor gradients and exact direct suffix/gripper step masking.
Budget<=2GPUh across at most2attempts; each<=45minutes, infrastructure-only retry.
Failure cannot be repaired by lowering tolerance or changing a scientific setting.
Engineering PASS is not learned-Q or robot-performance evidence.

## Stage 1 new data and representation

Before model execution, build an outcome-blind catalogue from pinned LIBERO-Plus
metadata. Exclude all prior exposed physical scene groups, conservatively
excluding entire ambiguous families. Select four remaining base-task families
by a frozen hash ordering, not by a pilot success rate. Cover all seven official
perturbation categories. Record task names, BDDL hashes, initial-state content
hashes, simulator seed, instruction, cameras and actual accepted state.
Different variant names or environment seeds are NOT proof of independent scenes.
Resolve shared initial-state files and physical scene aliases before splitting.

Target design, subject to metadata-only feasibility before registration:
288 training episodes (96 physical groups,3 perturbations per group),64 validation
episodes (32 new groups,2 perturbations),216 formal scenes (72 new groups,3
perturbations), balanced across the four tasks/categories as nearly as integer
counts permit. A state group never crosses partitions. No outcome-driven task
replacement, extra sampling until failures, or difficulty screening is permitted.
If the pinned population cannot support these counts without overlap, stop at
the metadata gate and revise the count BEFORE any outcome is observed.
This is a defined subset, not the full LIBERO-Plus benchmark or unseen-task claim.

Training behavior: uniformly random among four native candidates at every
replan, using an independent selection RNG and the unchanged execution horizon.
Only the selected executed prefix receives measured reward. Save all attempts,
raw/normalized candidates, executed prefix, actual m, per-step reward, R+1
observations, true termination vs benchmark time-limit, remaining steps, RNG,
policy memory, hashes, video, and prompt/config. No simulator oracle chooses
actions. Planner failures are not robot-policy failures and do not trigger
unregistered replacements. Unknown infrastructure errors stop the shard.

The first four NEW training-scene runs test collector integrity/cost, not class
balance or efficacy. If valid, count them once in the frozen288 cohort. Complete
the fixed cohort within its budget regardless of interim success rate. This new
design avoids interpreting a four-episode single-class pilot as population
saturation; it does NOT reopen the old stopped4/32-episode experiments.

After fixed collection, require>=12successes and>=12failures, with each class
represented in>=8distinct physical groups and all group-OOF folds containing
both classes. Otherwise report DATA_INSUFFICIENT_FOR_VALUE_IDENTIFICATION and
stop, without relabelling or expansion. Diversity is necessary, not sufficient.

Features: observation-only frozen WAM current-frame VAE features, proprio,
instruction embedding and remaining horizon. Audit the feature path before
extraction; do not use latent future observations or terminal data. Fit feature
scaling/projection only on the training side of each fold. No fixed model-feature
dimension is assumed until the actual source/tensor audit. Keep a small RGB
reference as an ablation, not as a replacement for the WAM feature critic.

## Stage 2 RL critic qualification

Three episode-group bootstrap ensemble members, each with twin action Q and V,
use action injection at each small MLP layer (initial width256, two layers).
Critic conditions on the normalized actually executed continuous prefix and
gripper state; deployment gradients mask the discrete gripper coordinate.
For partial terminal chunks, padded coordinates are masked, not fabricated.
Primary gamma=1 with explicit finite remaining horizon; actual length m updates
the next horizon and the reward sum. Benchmark timeout is terminal for the
finite-horizon task objective, not an infinite-horizon continuation.

    y = sum(k=0..m-1, gamma^k r_k) + (1-terminal) gamma^m V_target(s_next)
    L_Q = episode_equal_mean((Q1-y)^2 + (Q2-y)^2)
    L_V = episode_equal_expectile_0.7(min(Q1_target,Q2_target)-V)^2

Adam3e-4, batch128 with uniform group then episode sampling, target EMA0.005,
fixed20000updates, final checkpoint only. Split/bootstrap seeds202640101/102/103.
Freeze feature dimension, exact architecture and all training settings in a
machine-readable registration before fitting. Report all folds and all seeds.
Do not import the old14D/30-step critic into the new7D/10-step task.

Controls: same-target state-only (same observations/training updates), action
permutation within a current native bank, and fixed training-prevalence return
reference. The permutation changes only the selected candidate identity supplied
to Q, not environment labels; replay targets/bootstrap randomness are matched.
Train an MC-only version as a labelled ablation, not a substitute for RL.

Use group-disjoint OOF with final-step episode-equal TD/held-out return errors,
calibration and action-permutation sensitivity. All3seeds must outperform both
learned controls on the preregistered held-out return diagnostic; pooled paired
group-bootstrap improvement CI must exclude zero for the qualification claim.
These are necessary offline screens, not same-state causal-value proof.
Loss/AUC improvements alone never authorize a paper claim.

## Stage 3 online gradient and method validation

Freeze learned critic, normalization, support rule and online arm schedule before
the independent64-scene validation. No automatic outcome-dependent beta sweep.
Initial beta=0.1 and normalized explicit RMS cap0.05 are fixed method hypotheses;
if inactive or harmful, disclose failure rather than retune on the same validation.
Any later method revision uses another version and fresh validation population.

Use a native bank of4 plus one final candidate0 stream for each control, or a
guided candidate0 stream for gradient methods: FIVE model streams, not N4 cost.
All arms execute the same feature/critic gradient work in shadow when unused.
Same native seeds, sampler steps and per-stream cache policy; report measured
FLOPs/latency rather than equating stream count to exact computational equality.

Primary arms:
1. candidate0: native bank plus native candidate0 replay, execute candidate0.
2. random: same five streams, select uniformly from the native four.
3. critic reranking: same five streams, execute critic-best native candidate.
4. vanilla prefix-QGF: same bank plus guided candidate0, no support projection.
5. proposed prefix/support/consensus QGF: same bank plus constrained guidance.

Keep base N1 as a separate practical-cost reference. Primary hypotheses are
proposed vs random and proposed vs vanilla-QGF, with candidate0 as a required
non-harm check. Log predicted-Q change, gradient alignment, intervention rate,
step/final action deviation, clamp/abstention rate, recoveries/regressions, and
real terminal success. Q increase without real return improvement is a negative
mechanism result, not reward improvement. No oracle is consulted at deployment.

Validation gate: positive net gain over candidate0 and random, not worse than
vanilla-QGF, no invalid actions/contract violations. It is a screening decision,
not a significance claim. Failed gate stops this version. Only after passing,
freeze a group-level power/cost calculation and the formal protocol. Formal
data never tune the method. A fixed216-scene plan is not guaranteed powered;
repeated perturbations share physical groups and cannot be counted as216iid
replicates. Infeasible precision within the remaining budget is reported openly.

## Stage 4 formal evidence and ablations

Run all fixed matched scenes for all5arms without efficacy early stopping.
Use exact same accepted initial physical states and per-scene exogenous RNG
contract; a shared master seed is insufficient. Randomize/balance arm order.
Report all physical groups, episode outcomes and infrastructure attempts.
Primary uncertainty: paired physical-group bootstrap, task/category-balanced
success difference, with simultaneous/two-comparison multiplicity control.
Also report Wilson intervals and exact McNemar descriptively, clearly separating
episode-level iid summaries from clustered primary inference.

Report success,95%CI,rescue/regression/net,uncertainty,gradient/margin/switch,
candidate diversity, action safety/contract, wall time, all-attempt GPUh and
latency. Include negative and null results. A positive claim requires the
preregistered formal comparisons, not merely numerical+1 on a tiny set.

Ablations, after the primary method is fixed: remove projection; remove consensus;
full-horizon vs executed-prefix Q; MC-only vs TD/IQL; native visual features vs
RGB reference. Reuse the exact method/data/compute controls. The full-horizon
ablation cannot be confused with correctly aligned vanilla-QGF.

Second architecture: reuse a released Kairos implementation only after primary
validation and a new, separately registered gradient-hook/scene-cohort audit.
Its old stopped task/config remains stopped. If no second-backbone outcome is
available, narrow the paper claim rather than advertise general WAM gains.
Real robot validation requires user-provided access/safety setup; none is assumed.

## Budget and deadline

Official CVPR2027 dates checked2026-10-26: registration Nov10AoE, main paper
Nov16AoE, supplement Nov23AoE. Internal paper-ready target Nov12CST.
Source: https://cvpr.thecvf.com/Conferences/2027/Dates

Milestones are decision deadlines, NOT promises of positive results:
- Oct26-27: stage0, scene/exposure audit, collector and actual-runtime forecast.
- Oct28-30: fixed prospective data and RL-critic qualification.
- Oct31-Nov02: full sequential matched validation and go/no-go.
- Nov03-09: only if admitted, formal comparisons/ablation/second architecture.
- Nov10-12: freeze results, paper tables/videos, limitations and reproducibility.
- Nov13-16: independent check, anonymity, references and final submission review.

Ceilings including failed attempts: integration2GPUh, collection24GPUh,
feature/critic8GPUh, validation16GPUh, formal64GPUh, second-backbone/ablations14GPUh;
total128GPUh. These are upper limits, not a reservation or an instruction to
consume them. Before every stage compare fixed cohort cost from measured p90
episode time plus compilation/load overhead against its ceiling; if infeasible,
STOP and report the mismatch before running, without cutting a sample after
looking at outcomes. Keep>=20%cost contingency within each ceiling.

Currently job1593640 has2GPUs but only50GB node RAM; use at most one loaded WAM
in that allocation. It expires2026-10-29 15:50CST, well before the proposed
formal stage. No future capacity is assumed. A continuation allocation must be
verified before launching later jobs; never seize another actor's GPUs.

## Related work and novelty test

- QGF already provides test-time value-gradient guidance with an estimated clean
  action and no actor Jacobian: https://arxiv.org/abs/2606.11087
- Guided Action Flow already applies frozen-policy inference guidance using an
  offline IQL visual/action critic: https://arxiv.org/abs/2607.02092
- PreferenceFlow studies local intervention preferences and gradient regularizers:
  https://arxiv.org/abs/2609.36872
- SeeQ studies subtask-aware generalist values: https://arxiv.org/abs/2609.22085

Thus merely connecting WAM, RL and QGF, adding a stage classifier, or clipping
gradients is insufficient novelty. The proposed contribution must survive the
native-support/consensus ablations and demonstrate actual online benefit beyond
the same-critic vanilla QGF. A new name or more backbones is not evidence.
This is a targeted literature check, not a claim of exhaustive novelty clearance.

## Run ledger

All new work lives in qgf_gradient_v1 and new runs/qgf_gradient_* directories.
Write SHA/config/seed/source/process/resource evidence before interpreting output.
Keep audit PASS and clean process exit separate. The qwen automation is still
deleted; this request does not silently recreate it. No unattended later stage
is claimed until its dispatcher and actual Slurm step are recorded.

### User approved third integration attempt

After attempts1and2 failed for output-path serialization and shared-filesystem
compiler-temp cleanup respectively, the user explicitly approved one additional
minimal repair retry within the unchanged2GPUh aggregate ceiling. See
STAGE0_RETRY2_APPROVED.json. Only TMPDIR moves to a unique node-local directory;
all models, scientific settings, compile flags, seeds and gates stay fixed.
This supersedes only the two-attempt operational limit, not any scientific gate.

### Continued execution and45minute monitoring authorized2026-10-26

The user explicitly requested completion of the new collector's action/reward/
RNG audit, training collection, RL critic and matched online comparisons, and
a new45minute task to supervise and advance the experiment. Heartbeat
qgf-wam-rl is now ACTIVE; this supersedes only the earlier run-ledger statement
that no new automation was requested. The old qwen task remains deleted.
Scientific gates/budgets remain fixed. Read HANDOFF.md and
COLLECTOR_CONTRACT_V1.md for the current registered execution and exact status.
Stage0 completed ENGINEERING_PASS/clean exit; no learned-Q efficacy is implied.

### Decision-time input clarification before any real critic fit

DECISION_TIME_RL_INPUT_V1.md corrects an information-flow issue in the initial
primitive:actual terminal execution lengthm is a post-action variable and must
not be an input mask of the current critic. The committed macro-action plan has
known lengthL=min(10,remaining_steps),with stop-on-terminal execution semantics.
Q receives this actual selected predecision plan and a mask afterLonly. Actualm
and its reward mask enter the semi-MDP target,not current features. Thus a
terminal short rollout does not expose its outcome to Q via a short mask. This
supersedes only the earlier ambiguous partial-terminal mask sentence. Collection,
stored actual actions/rewards,all seeds,cohorts,thresholds and budgets are fixed.
No unselected candidate gets a label. The correction was derived structurally
before real fitting/validation,without selecting on observed method outcomes.

matched_iql.py provides the real-training primitive with known planned masks
and identical detached TD labels for action,state-only and within-bank controls.
The original IQLLearner remains a retained engineering primitive and must not be
used for real qualification. features.py/training_data.py implement current-only
raw representation and group bootstrap inputs,with actual GPU encoder audit and
full corpus/trainer registration still pending. No actual critic has been fitted.
