# Matched Fresh Reference Engineering Retry3

Parity probe completed with ZERO executed robot actions. Candidate commit0,
commit1, reset-repeat, fresh-native repeated reset/act and legacy-native repeated
reset/act all had max error0. Candidate0 versus fresh native also had error0.
Both fresh services differed from the existing reference by0.0029296875.
Checkpoint/source/config health fingerprints agree. This isolates cross-service
runtime/lifetime differences; the underlying hardware/backend/state cause is
NOT yet established. Do not claim a proven fix to the existing service.

New named retry3 performs the full engineering random-N4 rollout against a
fresh unmodified native reference launched alongside the candidate service on
the same allocated node. Official checkpoint, denoise10,execute10,seed20261022,
16D action, success and strict1e-6 tolerance remain unchanged. This explicitly
changes the reference service instance, not the acceptance tolerance or policy.
Old native results remain separate and are NOT paired with this new runtime.

Use the same excluded engineering scene202619100 and selection RNG202619001.
No scene or policy-success filtering, no training labels admitted from smoke.
Three fresh distinct allocated GPUs,45minute hard cap=2.25GPU-hours maximum.
Check initial candidate0/native exact parity, per-replan proposal/commit matching,
finite/nonidentical candidates and full R+1 transition audit. If it fails, retain
evidence; no bulk collection or critic training is automatically authorized.
