# Simple-WAM LIBERO-Plus parity v1

Status: `PREREGISTERED`

This is an infrastructure and official-baseline parity gate. It is not a QGF
result and cannot be used as a performance estimate.

## Frozen condition

- Source commit: `396cba18c318bc33a1ef42513b85298e3016e28a`.
- Checkpoint SHA256:
  `2b1e2f36ff06e701026028402976a4174be23ab48469289d01c93ce541b21d66`.
- Dataset statistics SHA256:
  `6b49b1bdf37268e3f1e6e621c4d5cb03ba028f3fabff3df3c68067c0a7c91c69`.
- LIBERO-Plus archive SHA256:
  `3bad55e3f195ee734fd24eebdcd47fee756255b604dffc2011b726f5a18381f8`.
- Suite/task: `libero_10`, task 0, one episode, seed 10000.
- Official dual-camera preprocessing, native 7D action, 8D state, action
  horizon 32, replan interval 10, and official success criterion.
- Ten inference steps, frozen future-video noise, compiled action path, and
  text-encoder offload, matching the released LIBERO evaluation recipe.

## Required evidence

- Complete episode result and video, including accepted seed and initial state.
- Checkpoint/statistics/source identifiers and action-contract audit.
- Environment steps, success, inference latency, wall time, and peak VRAM.
- No missing/unexpected checkpoint keys and no post-decoding action changes.

Budget: expected 10-25 minutes, hard 60 minutes and 1 GPU-hour on one verified
idle allocated A800. Infrastructure failures are retained and may receive only
minimal repairs that do not change task, seed, model, action, or success rule.

Passing this gate only admits the same-observation native N4 candidate and RNG
replay audit. It does not admit a critic or an online QGF comparison.
