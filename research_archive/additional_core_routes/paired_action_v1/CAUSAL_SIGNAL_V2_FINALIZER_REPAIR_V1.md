# Causal Signal V2 Finalizer Metadata Repair V1

The frozen 16-group execution completed cleanly, but the original zero-GPU
finalizer stopped before creating an output because it expected a post-pilot
`registration["pilot"]` field that was never added to the main preregistration.
The pilot report hash is already frozen by the independently generated
`causal_signal_v2_pilot/AUDIT_REPORT.json`, whose status is
`CAUSAL_SIGNAL_V2_PILOT_PASS` and whose error list is empty.

This repair preserves the original failed finalizer and adds a new finalizer
that verifies the original finalizer and metrics source hashes against the
preregistration, verifies the pilot audit file, and then calls the same frozen
`qualify()` function. It changes no population, result, endpoint, bootstrap,
threshold, task, seed, action, or scientific interpretation. It uses zero GPU.

