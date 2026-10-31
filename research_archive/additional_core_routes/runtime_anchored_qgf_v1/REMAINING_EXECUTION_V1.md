# Runtime-Anchored Remaining Execution V1

The repaired fixed pilot completed cleanly in step `1593640.411` and the
independent audit returned `RUNTIME_ANCHORED_PILOT_AUDIT_PASS`. The remaining
scope is exactly registration indices 1 through 15 from manifest SHA
`67210bb4c1f1907c990ed699f8d871f5692416201fec878f7abffacec3527d82`.

Each group uses the unchanged runner and a separate output directory. A strict
dummy/prefix physical replay mismatch is recorded as unavailable and the fixed
queue continues; every other error stops the queue. No group is replaced or
retried. Pilot plus failed initial pilot plus remaining execution retain the
14,400 allocated-GPU-second cap.

