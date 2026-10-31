# Fresh-environment deterministic replay A-B-A gate V1

The in-place checkpoint route is frozen failed: step1593640.361 completed the
100-action A0 branch but its first rebuilt-renderer raster did not equal the
checkpoint raster. This gate does not weaken that result. It replaces native
handle restoration with complete deterministic reconstruction from the frozen
initial scene for every branch.

Use only registered `train_0205`, environment seed and initial state. For each
branch A0, B0, A1 and A2, create a fresh official environment, reset all global
Python/NumPy/Torch CPU/CUDA RNGs to the registered seed, perform the same 30
official dummy waits, and replay the same 100 archived executed prefix actions.
Every dummy and prefix reward, done, success and simulator state must exactly
match the archived trajectory before the branch starts.

At each reconstructed boundary save full MuJoCo integration state, flattened
simulator state, proprioception, global RNG digest, returned dual-camera raster
and direct live dual-camera raster. All four boundaries must be bitwise equal.
Execute frozen candidate-0 A for A0/A1/A2 and candidate-1 B for B0. Save each
step's reward, done, success, proprioception, full MuJoCo integration state,
simulator state, RNG digest and both raster digests. A0/A1/A2 must be bitwise
equal at every step; B must perturb the trajectory. Frozen actions are submitted
without modification and replay error must be <=1e-6.

No WAM or critic is loaded and no QGF benefit is measured. One allocated idle
A800, 8CPU/45GB, inner1200s and Slurm1300s. This is one bounded attempt within
the remaining1313s engineering cap. Failure is frozen without changing seed,
scene, action schedule, horizon, renderer, success rule or equality thresholds.
