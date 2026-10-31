# Real-runtime A-B-A restoration gate V3

V3 preserves V2's dictionary repair. It replaces V2's erroneous placeholder
`coverage nodes > 900` assertion with the exact independently frozen V2 capture:
792 nodes with kind counts external227/list219/array126/object84/dict82/tuple46/
ordered_dict8, plus required controller, observable, robot-history, MuJoCo and
renderer path checks. V2 produced this coverage before every A/B branch action;
its COVERAGE.json SHA is f0f53d04671e0b52ba524e7886210ba032c70a5a4789d517fba9a83623f83ec9.
No serialization behavior, task, action, threshold or branch is changed.

V2 differs from the preserved failed V1 only by admitting immutable dictionary
keys `None`, exact `str`, and exact `int`. This covers the official static
MuJoCo name map observed in V1; all other key types still fail closed. The
scene, action sources, branch order, comparison fields and thresholds below are
unchanged.

One bounded engineering gate on the first frozen paired-action registration
entry, train_0205. Reconstruct the original state exactly through 30 official
dummy waits and the first 100 audited executed actions. Every replayed reward,
done, success and flattened simulator state must match the frozen trajectory.

At the model-step-100 boundary, capture fail-closed Python/controller/robot/
observable state, MuJoCo integration state, Python/NumPy/Torch CPU/CUDA RNG,
static XML/callback/model identities and live direct dual-camera raster. Unknown
types or fields stop before branch execution. The renderer is rebuilt after each
restore and its direct raster must match exactly.

Freeze A as the concatenated candidate-0 native first-10 prefixes from archived
transitions 0010..0019 and B likewise from candidate 1. Execute A, restore, B,
restore, A1, restore and A2. Each branch is 100 true environment actions unless
official terminal occurs. A/A1/A2 must match bitwise at every common step for
reward, done, success, proprioception, complete runtime-graph digest, MuJoCo
integration state, returned policy raster and direct live raster. Action replay
error must be <=1e-6. B must differ from A. No WAM, critic, label fitting or
paired diagnostic result is produced by this engineering gate.

Single attempt, one allocated idle A800, 8CPU/45GB, inner 1200seconds and Slurm
hard 1300seconds. This consumes at most the remaining1549seconds of the frozen
0.5GPUh engineering budget. Process exit and Slurm state are audited separately.
No automatic retry or threshold relaxation.
