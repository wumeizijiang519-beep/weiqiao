# One bounded CPU registration-serialization repair

All288episodes collected and independently audited. GPU333 completed0:0/7496s;
CPU334 audit completed0:0/931s. Original dispatcher completed0. One-shot CPU
aggregation335 failed1:0/238s before data qualification because it required saved
registration.json bytes equal the original pretty-printed shard files. The
collector serializes the same JSON object differently. Read-only audit found
all four decoded JSON objects equal, no differing fields; both sets of raw SHA
are retained. No episode, action, observation, seed, label or outcome is changed.

Keep aggregate_training_v2.py and335failed logs unchanged. New separately named
aggregate_training_v2_format_repair.py differs only by a registration verifier:
original file must still match precollection SHA; retained saved file must match
its newly pinned diagnostic SHA; decoded entire objects must be identical. No
semantic registration difference is permitted. All other audits and scientific
qualification gates remain copied byte-for-byte in logic. No old episode audit
or rollout is rerun; complete aggregation must finish once to certify the union.

One bounded CPU retry2CPU/8GB/zeroGPU/hard90minutes, new log/run. Scientific
DATASET_RESULT is never overwritten. Register repaired source SHA before retry.
Any further error needs first-cause audit, not automatic unbounded retries.
All failed CPU audit costs retained but0GPU. Completed collection25418+7496=
32914GPU seconds; integration1796incl resource failures; total34710GPU seconds
before new feature/critic work. Resource supplement738must be counted once.
