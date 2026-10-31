# Fresh-environment replay A-B-A gate V2: renderer warmup isolation

V1 completed all four branches with exact reconstructed boundaries and exact
A-repeat reward, terminal, proprioception, full MuJoCo integration state,
flattened simulator state and RNG. Only raster hashes failed: the first measured
fresh environment A0 differed from both A1 and A2 at returned-raster steps3/4
and direct-raster step3, while A1 and A2 were mutually identical. This pattern
supports a process-first EGL context warmup fault, not a physical-state mismatch.

V2 is explicitly authorized by the user's request to repair. It adds exactly
one sacrificial `WARMUP` reconstruction and A action branch before the measured
A0/B0/A1/A2 set. The warmup is saved and costed but excluded from every gate and
future scientific denominator. It does not choose a scene, seed, action, outcome
or branch based on performance. All measured branches still use fresh official
environments and the same frozen train_0205 seed, initial state, 30 dummy waits,
100 archived prefix actions and candidate-0/candidate-1 actions.

Every reconstruction must match archived feedback and simulator state. All four
measured boundaries must be bitwise equal. A0/A1/A2 must remain bitwise equal at
every step for reward, done, success, proprioception, full MuJoCo integration
state, flattened state, global RNG, returned dual-camera raster and direct live
dual-camera raster. B must perturb the trajectory. Action error remains<=1e-6.
No pixel tolerance, post-hoc alignment or archived-image substitution is used.

No WAM or critic is loaded and no QGF benefit is measured. One allocated idle
A800,8CPU/45GB, inner1200s/Slurm1300s. Prior engineering cost586GPU seconds is
retained; this single repair must fit the remaining1214seconds of the0.5GPUh cap.
Failure is frozen without another renderer retry.
