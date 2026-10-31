# Runtime-Anchored Registration Repair V1

Step `1593640.410` failed before candidate generation and before any branch
action because the Runtime-Anchored registration copied the sparse V2 manifest
entry rather than the already frozen enriched V2 authorization entry. The
runner therefore could not read `task_name`; the same source authorization also
contains the existing `state_sha256` and `prefix_actions_sha256` receipts.

The repair cross-references each unchanged development physical group to its
frozen V2 authorization and copies those three existing execution receipts.
It changes no group, split, scene, state, prefix, model, seed, candidate,
horizon, metric, threshold or budget. The original registration and failed
pilot remain immutable. One repaired pilot attempt is allowed after independent
CPU registration audit; no further automatic retry is allowed.
