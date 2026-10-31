# Cross-service Candidate0 Diagnostic, No Gate Relaxation

Retry2 failed BEFORE executing actions: native versus candidate0 max abs0.00292969,
62/160 elements outside frozen absolute tolerance1e-6. Keep FAILED/trace/SHA.
Do not count this as a robot failure or launch bulk data. Do not relax tolerance.

Capture the SAME previously feasible engineering scene202619100 and save the
first observation as replayable JSON. Execute ZERO robot policy actions. Compare
candidate/commit0, reset/repeat candidates, selected1/commit1, repeated native
reset/act, and fresh native versus existing native versus candidate. This tests
transaction reproducibility separately from process lifetime/backend differences.
No single hypothesized cause is assumed proven. Preserve all raw output arrays.

Use an unmodified official native entry point and existing candidate entry point
on two fresh isolated GPU processes, plus one simulator GPU for scene capture.
Fresh native seed/steps/checkpoint/config match frozen baseline. Compare the
existing isolated native reference too; do not change its running process/code.
Three assigned GPU tasks,20minute total cap=1GPU-hour for new tasks; conservative
1.34GPU-hours including already-loaded reference. Existing native receives only
serial diagnostic requests and is reset afterward. No training labels/results.

PARITY_PROBE_COMPLETE means diagnostic evidence saved, NOT gate admission.
Only evidence-supported minimal corrections may proceed in a new named retry.
