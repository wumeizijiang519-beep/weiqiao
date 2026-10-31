# Dynamic A-B-A gate V2 minimal pre-branch repair proposal

V1 step1593640.356 failed after the registered prefix reconstruction but before
checkpoint capture completed and before any A/B branch action. The fail-closed
dictionary contract admitted only string and integer keys. The official static
MuJoCo model name-to-id map `_geom_name2id` contains one legitimate `None` key
alongside string names. Runtime inventory retry2 had already recorded that key,
but the V1 adapter omitted it.

The proposed V2 change admits exactly `None`, `str` and exact `int` dictionary
keys, all of which are immutable scalar tokens already supported by StateGraph.
It does not admit tuples, objects, NumPy scalars or arbitrary hashables. A unit
test mutates and exactly restores a `None` key. Preserve all V1 source, logs,
54 charged GPU seconds and failed directory. Task, boundary, action schedules,
SHA inputs, branch order, exact thresholds, renderer requirement and remaining
1495-second engineering budget are unchanged.

Do not launch V2 without explicit user approval because V1 was preregistered as
a single attempt with no automatic retry.
