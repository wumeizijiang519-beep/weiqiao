# Deferred real encoder audit launch preparation

run_encoder_audit.sh is prepared but NOT launched or registered with a dataset
digest yet. Require successful full288aggregation scientificADMIT and cleanCPU
process336, no other encoder run/result, fresh owned allocation/GPU0idle. Never
launch during current unqualified aggregation. A CPU helper/test PASS does not
replace the real current-only GPU encoder gate.

Before launch create ENCODER_AUDIT_REGISTRATION.json with actual dataset SHA,
all runtime/encoder/features/core/data_contract/launcher dependency SHA, dataset
and resource cost supplement hashes, selected fixed first/last manifest endpoints,
phase budget and run path. Main audit already verifies manifest/DATASET_RESULT
sidecar, frozen WAM strict accounting, fixed A-B-A input/RNG/feature replay1e-6,
actor requires_gradfalse/no grads, registered buffers unchanged, future0frames.
Wrapper independently checks registered source/data SHA and saves process/cost.

Request ONEallocatedgpu1A800 GPU0,8CPU/45GB,hard<=22minutes with an outerSlurm
time plus inner1200s timeout. Control directory must be new; Python audit owns
its nested audit/ directory. No robot environment or model action is executed.
One attempt, failure evidence retained. Encoder cost belongs to shared8GPUh
feature/critic phase, not original Stage0 integration. Keep20percent reserve
and include resource supplement738once in cumulative totals. Existing strict
WAM load measured184.9s and zero-action full integration431s provide conservative
prelaunch engineering load estimate; this is NOT a measured feature p90. The
subsequent fixed-first-two feature pilot must establish actual p90 before286
remaining extraction. No actor/checkpoint/model/seed/science change.
