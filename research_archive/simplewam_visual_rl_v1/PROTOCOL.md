# Simple-WAM Visual RL/QGF V1

## Research lineage and CVPR hypothesis

- `tau0-qgf/docs/visual_rl.md` is the implementation blueprint that combines an
  external visual RL token, an offline TwinQ critic, candidate reranking, and
  Q-gradient flow guidance.
- `Yyshadow/openpi-RLT` is the reference for RL-token representation and the
  actor-critic/replay separation around a frozen VLA policy.
- `zhouzypaul/qgf` is the reference for keeping the behavior-cloned flow policy
  and TD critic separate, then applying critic gradients only at test time.

The research question is not whether the Tau0 code can be mechanically ported.
It is whether an external visual token and separately trained critic can provide
stable, action-sensitive value gradients that improve a frozen world-action
model on held-out LIBERO tasks. The primary comparison is frozen Simple-WAM
versus equal-compute candidate reranking versus Simple-WAM QGF. A publishable
positive claim requires held-out task success improvement, not reconstruction,
critic loss, gradient magnitude, or successful software integration.

## Purpose

This branch returns to the original visual-RL pipeline:

1. compress frozen world-action-model visual hidden states into an RL token;
2. train an offline TwinQ/value critic on real executed macro-transitions;
3. use the same frozen TwinQ for candidate reranking and action-space Q-gradient
   flow guidance.

The policy backbone is the frozen Simple-WAM LIBERO checkpoint. Tau0 is not a
runtime dependency and no Tau0 weight, latent, scheduler, or action convention
is used. The reusable parts are only the external token autoencoder, IQL loss,
TwinQ aggregation, and actor-free Q-gradient mathematics.

## Frozen mapping

| Original visual-RL role | This branch |
| --- | --- |
| frozen Tau0 VAM | frozen Simple-WAM video expert |
| Tau0 visual hidden cache | position-aware Simple-WAM video hidden states |
| Tau0 action flow | frozen Simple-WAM action expert and continuous scheduler |
| RL token | external position-aware TokenAutoencoder output |
| offline critic | external TwinQ plus expectile value model |
| rerank/QGF score | the same final online TwinQ checkpoint |

The RL token is never inserted into Simple-WAM and Simple-WAM is never updated.
Visual-token training uses reconstruction only. Reward, success, progress,
future observations, candidate identity, and terminal state are forbidden from
the token encoder input and target.

## Observation and action contract

- Benchmark: LIBERO through the existing Simple-WAM two-camera evaluator.
- Frozen policy action block: `H=32`, `A=7` continuous model coordinates.
- Critic action: the predecision committed prefix of length `K=10` from the
  existing 288-episode training contract. If fewer than ten task steps remain,
  only that known predecision length is valid and the remaining coordinates are
  masked. The realized post-action termination length is never a Q input.
- The reward target sums only measured rewards from the realized `m<=K` steps
  and bootstraps by `gamma**m` when the finite task did not terminate.
- Proprioception and actions use the exact frozen Simple-WAM dataset statistics.
- Gripper gradients are masked during QGF; no discrete gripper value is changed
  by guidance.

## Visual feature contract

The uncompiled frozen Simple-WAM video prefill is run with the same current
two-camera image, instruction, normalized proprioception, future-video noise,
seed, timestep, and attention mask used by policy inference. Selected video
expert layers are captured after their post-attention block. Only temporal plane
zero is retained. Every feature has coordinates `(layer,camera,time,row,column)`.
Future video planes and action tokens are excluded.

The feature pilot must prove:

- repeated extraction is bitwise identical;
- changing action sampling noise does not change visual features;
- changing either current camera changes at least one visual feature;
- no input sensor, policy weight, RNG stream, or policy output is mutated;
- native action output with the bridge disabled is equal within `1e-6`.

## Training stages

### Token stage

Train the external position-aware autoencoder against `LayerNorm(F)` only.
Freeze the selected checkpoint and its normalization metadata before critic
training. Token validation is reconstruction-only and is not action-value
evidence.

### Critic stage

Use the frozen token encoder and fixed physical-group-disjoint folds. Train
TwinQ/value with IQL on the real selected native prefix and measured transition.
Matched controls are state-only and within-native-bank action permutation. Use
three fixed seeds and equal updates/batches/targets.

Qualification requires every seed to beat both controls on group-equal held-out
error, remain sensitive to within-bank action permutation, and have a physical-
group bootstrap lower 95% bound above zero. Otherwise freeze a negative result;
do not add seeds, updates, or tune on validation/formal data.

### Deployment stage

The final qualified TwinQ checkpoint is shared by both modes:

- rerank scores complete frozen Simple-WAM candidates;
- QGF evaluates the estimated clean `K`-step prefix at each registered action
  denoising step and differentiates only with respect to that action prefix.

No gradient enters Simple-WAM or the token encoder. The native policy,
candidate count, denoising steps, and random seeds are identical across baseline,
rerank, and QGF arms. A held-out online comparison is required before claiming
QGF benefit.

## Stop conditions

Stop this configuration if the visual feature gate fails, the fixed training
population is insufficient, the critic qualification fails, or held-out QGF
does not improve both candidate0 and random while not losing to rerank. Engineering
PASS, reconstruction loss, critic training loss, or nonzero gradients are not
online QGF results.
