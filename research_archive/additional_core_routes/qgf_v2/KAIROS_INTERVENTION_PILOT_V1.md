# Kairos Randomized Intervention Pilot V1

## Frozen scope

- Training-only task: `libero_mix / Background Textures / task0`.
- Four episodes, two independent shards; no validation or formal seeds.
- Shard 0: environment seeds `[202633101, 202633102]`, initial-state indices `[1, 2]`, selection seeds `[202633501, 202633502]`.
- Shard 1: environment seeds `[202633201, 202633202]`, initial-state indices `[3, 4]`, selection seeds `[202633601, 202633602]`.
- At every replan boundary, generate native N4 from the same current observation using seeds `[10000,11000,12000,13000]` and uniformly select one with the frozen selection RNG.
- Execute only the selected chunk for at most 10 environment steps. Unselected candidates receive no reward label.

## Required evidence

- Persist every candidate chunk/hash, selected index, selected/executed first-action error, actual rewards, finite-horizon return, observation image, latency, episode result and rollout video.
- All transitions must have shape `[4,32,7]`, finite candidates, four unique hashes, and selected/executed first-action max error at most `1e-6`.
- Pilot passes only if all four episodes and audits complete and outcomes contain at least one success and one failure.

Failure to obtain both classes freezes this task/config; do not screen another seed or silently expand the pilot.
