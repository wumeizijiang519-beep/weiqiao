# Paired native-action diagnostic V1

Authorization: user approved POST_STOP_REVIEW_V1 on2026-10-27CST. This opens
only this new diagnostic; prior negative results and scientific stops remain.
Frozen WAM Simple-WAM, checkpoint/statistics/runtime unchanged. No critic fit,
validation/formal trial or backbone change is authorized by a diagnostic pass.

## Prospective population and cost

From the original288train metadata only, select4distinct physical_input_group
hashes per family by SHA256('paired-action-v1|'+family+'|'+group), then one entry
per group by SHA256('paired-entry-v1|'+episode_id). Never read rewards to select.
Use the logged100-model-step boundary; terminal/missing boundaries remain
unavailable in the16-state denominator, no replacement. This conditions on
survival at100steps and is not a population-wide efficacy claim. Existing
training exposure is disclosed; original64validation/216formal stay untouched.

First freeze metadata and perform CPU-only source inventory. Next implement
and preregister complete state serialization before a bounded dynamic gate.
At most0.5GPUh restoration engineering and2GPUh diagnostic, within the existing
128GPUh total (all previous12.3828GPUh costs retained). At most1GPU WAM on
gpu1/50GB. No automatic retries, no threshold changes or substitute scenes.
Source audit is not a dynamic pass. If restoration fails, stop actions.

## Restoration contract

Inventory simulator integration/solver state including warm starts, control
and applied forces, robot/controller/gripper/interpolators, task counters and
success state, observable caches/delays/noise, Python/NumPy/Torch CPU/CUDA and
independent generator state, WAM caches/buffers, and measured observations.
Do not claim a full snapshot from qpos/qvel or retained image substitution.
Unknown mutable fields or unhandled native objects fail closed. Source hashes
and explicit exclusions must be published before dynamic testing.

Reconstruct the registered boundary without relabelling the original episode.
Capture a new complete live checkpoint and measured policy input. Validate
candidate0 A-B-A replay after a different branch: exact simulator/controller/
RNG states and rewards/terminal/proprio across100steps (or terminal), identical
first policy input, and action replay error<=1e-6. Raw future raster hashes
must match for this paired-policy study; no tolerance relaxation or archived
sensor substitution. Two repeats, zero critic training. Cost pilot and exact
implementation/source registration required before dispatching WAM actions.

## Conditional paired measurement

Native N4 seeds10000/11000/12000/13000 from the same observation/memory;
float32[4,32,7], native gripper-1/0/+1. Execute each prefix up to10steps,
then native candidate0 closed-loop continuation to100total steps or official
terminal, with matching initial caller RNG and frozen continuation schedule.
Each branch starts from the same audited checkpoint, not the previous branch.
Predeclare branch order by group hash. Only actually executed branches receive
measured sparse reward and official success labels; unsupported branchesNaN.
No counterfactual labels from generated video, critic predictions or experts.
Save stepwise feedback, snapshots, observations, actions, hashes, video, costs.

Primary diagnostic: count physical groups with differing branch success within
the fixed100step horizon. Report all16availability and complete paired return
vectors, per-family results and exact group-level uncertainty. No iid treatment
of branch rows. Proceed to a separately preregistered learning study only if
at least12/16states fully audited and at least4distinct groups across at least
2families show differing binary outcomes. Otherwise freeze NO_IDENTIFIABLE_SIGNAL
for this diagnostic; do not extend horizon or sample extra states. This threshold
is a minimum feasibility screen, not significance, learnability or QGF efficacy.

Branches/oracle returns are training-only and prohibited at deployment. A
qualified critic plus fresh matched-compute online tests would still be needed.
