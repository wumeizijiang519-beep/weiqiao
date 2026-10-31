# Simple-WAM Randomized Intervention Pilot V1

## Scope

This is a training-only data qualification pilot. It is not online QGF evaluation and no
unexecuted candidate receives a label. It follows the passed Simple-WAM parity and native-N4
gates without changing the model, task checkpoint, action decoder, or success criterion.

## Frozen conditions

- Benchmark/task: `libero_10`, task 0 (the parity task), official initial states 1-4.
- Four episodes in two independent two-episode shards.
- Shard 0: environment seeds `[202634101, 202634102]`, initial states `[1, 2]`,
  selection seeds `[202634501, 202634502]`.
- Shard 1: environment seeds `[202634201, 202634202]`, initial states `[3, 4]`,
  selection seeds `[202634601, 202634602]`.
- Every replan generates native candidates with seeds `[10000, 11000, 12000, 13000]`
  from the same current observation and model state. A selection RNG uniformly chooses one.
- Only the selected candidate is executed for at most 10 environment steps. Its observed
  reward sequence and undiscounted finite-horizon return are recorded. Unselected candidates
  have no outcome label.
- Official 30 dummy waits, dual-camera/state preprocessing, 32-step action horizon, binary
  gripper, 10 denoising steps, frozen future-video noise, compiled action inference, and
  official task success remain fixed.
- Two explicitly allocated A800s may run the shards independently. Hard cap is 60 minutes
  per shard and 2 GPU-hours total.

## Required audit

Save every current and next observation, all four candidate chunks and hashes, selected index,
executed action prefix, rewards, finite-horizon return, terminal flag, inference latency,
candidate diversity, and video. Each selected committed action must exactly equal its stored
candidate prefix (maximum absolute error zero).

## Admission

PASS requires all four episodes complete, every transition finite with shape `[4,32,7]`, four
unique hashes per replan, positive diversity, exact selected-action commit, and at least one
successful and one failed episode. A single-class result or audit failure freezes this
task/configuration. Seeds, task, thresholds, and success rule may not be changed to rescue it.
