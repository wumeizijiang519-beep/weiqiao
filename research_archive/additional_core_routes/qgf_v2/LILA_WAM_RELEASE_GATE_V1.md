# LiLa-WAM Release Gate V1

## Scope

LiLa-WAM is the B3 fallback after Simple-WAM failed its frozen Train32 class-diversity
gate. This gate is CPU/network only. No GPU work is allowed before code license,
checkpoint, adapter, action contract, and runtime requirements are all verified.

## Frozen sources

- Official repository: `teee000/LiLa-WAM`.
- Source commit: `b6a2095d76927119bcfc0d2ca04eb5cea98d10d8`.
- Official RoboTwin checkpoint repository: `yangfan97/LiLa-WAM_RoboTwin2_0`.
- Checkpoint revision: `93ab191b2500aa37322244c4ae0e84eed1e848ee`.
- Official checkpoint metadata advertises Apache-2.0.

## Admission

The route is admitted only if the source release contains an explicit reusable license,
the official RoboTwin checkpoint and normalization/config sidecars are public, and the
provided RoboTwin bridge can execute without changing model or benchmark semantics.

## Frozen decision

`BLOCKED_NO_SOURCE_LICENSE`. The pinned official source archive contains no `LICENSE`,
`COPYING`, or other explicit source license. Model-card licensing does not grant a source
code license. Do not download the 1.27-GB checkpoint or use GPU resources for this route.
Retain the source archive, SHA256, repository metadata, and this negative release result.

