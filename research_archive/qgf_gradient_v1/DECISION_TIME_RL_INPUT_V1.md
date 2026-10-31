# Decision-Time RL Input Contract

Status2026-10-26: CPU implementation and synthetic checks; real feature-tensor
audit, full dataset qualification and fitting registration are still required.
This correctness clarification precedes any real-data critic fit or validation.
It follows a structural information-flow review, not observed model performance.
Collection, scene population, actions, rewards, seeds, budgets and all scientific
qualification thresholds stay fixed. No collector is edited or restarted.

## Separate a Committed Plan From Its Actual Feedback Length

At a replan boundary the known action is the selected native prefix plan of
length L=min(10,remaining_steps). It is committed with the benchmark's ordinary
stop-on-terminal rule. Actual execution may stop after m<=L steps when the task
terminates. m is determined after the action, so supplying m or its mask to the
current Q network would leak future termination and differ from online inputs.
This issue was found by inspecting the earlier primitive IQLLearner, which
required mask.sum==m. That primitive must not be used for the real qualification.

The Q input therefore contains the selected predecision native plan of lengthL,
canonical normalized binary-gripper values, and a mask derived only from known
remaining horizon. Coordinates afterLare absent/NaN-masked. The selected plan's
unused terminal tail was a real predecision proposal, not a fabricated executed
action or a separate candidate reward. No unselected plan gets a reward label.
Logging still preserves only the m real executed actions and their real feedback.

For targets, sum only the m measured per-step rewards and bootstrap with
gamma**m times V(s_next),masked by true finite-task terminal status. Neitherm,
terminal status nor eventual success is fed into Q(s,a)or V(s). Current remaining
horizon is known; next remaining horizon is used only with the next observation.
No full32step proposed action is assigned a10step-transition label.

The structural correction is shared by action-aware,vanilla-QGF and supported
QGF. Their action horizon,gradient mask and frozen scientific criteria agree.
Changing the future terminal length alone must leave a current Q input identical;
test_features_data.py explicitly verifies that property. test_matched_iql.py
rejects the old use of actual length as a predictor mask.

## Same-Target Controls and Bootstrap

matched_iql.py creates identical initialized copies for action,state-only,
within-bank permutation,and the labelledMCablation. For the three TD models,
every update uses exactly the same batch,bootstrap groups,episode weights and
detached TD target from the action learner's EMA value reference. Controls do
not silently use differently evolving Bellman labels. Their value heads retain
the same expectile objective and network size. State-only receives zero action
coordinates and the known planned-length mask,which is already a function of
the observed remaining horizon. It receives no realized termination length.

The permutation model receives an independent frozen within-bank identity,
including the legitimate1/4identity probability,with the original actual reward
and transition. Held-out true logging-policy finite returns remain the common
qualification diagnostic; lower fitted shared-TD loss is insufficient. A shared
bootstrap reference is not independent causal evidence and is reported as such.
The MC action ablation uses actual future logged return with the same inputs;
it is not a replacement for the preregistered TD/IQL primary learner.

GroupEpisodeSampler resamples physical groups,then chooses group/episode/real
transition. Its episode-count weights compensate group-first sampling for an
episode-equal objective in the resampled population. Fold isolation happens
before bootstrap; no held-out group can enter fitting or scaler estimates.

## Current-Only Frozen WAM Representation

features.py uses the exact official dual-camera observation preprocessing,
current-image _encode_input_image_latents_tensor,official prompt encoding,
normalized8Dproprio and remaining_steps/700. It never calls joint future video
generation and never consumes reward/terminal/success as features. Spatial VAE
latents from one current frame are adaptively pooled to4x8per channel; context
uses the official returned context mask. The source returns visible zero-padding
positions,so the pool preserves that behavior instead of claiming the mask
contains true token lengths. Actual latent channels/dimension must be measured
and frozen by a real encoder-only GPU audit before fitting; no shape is assumed.

Global Python/NumPy/Torch CPU/CUDA RNG is restored around representation calls.
A GPU audit must repeat observationAafter observationBto exclude hidden temporal
cache effects and record source/checkpoint/config/tensor hashes,RNG,dtype,latency
and peak memory. It must pass before bulk extraction. No second WAM is loaded
while the current50GBallocation holds the collector.

FoldScaler fits mean/std only on training-side current observation rows,
standard-deviation floor1e-5,and keeps all raw dimensions. Validation outliers
cannot update it. No global/cohort-fit PCA or normalization is performed.
Store raw frozen features so each group-disjoint fold can fit its own scaler.

## Remaining Work Before Fitting

After fixed288data admit,freeze encoder audit and exact feature dimension,run
an actual cost probe within feature/critic8GPUh,register the feature corpus,
fold/bootstrap manifests and full20000update training jobs. Implement the full
dataset loader,OOF prediction,final-step checkpoints,held-out return/error and
paired physical-group bootstrap reports before launching any real fit. Only
the original stable action-evidence gates can admit an online selector.
