# Initial-State Hash Repair Proposal

Status: proposal only; no retry is authorized by this file.

Retry 1 used `data_contract.array_hash(initial)` to validate the registered
`state_sha256`. The manifest was created with
`sha256(initial.tobytes())`. `array_hash` additionally includes dtype and shape,
so every valid frozen state is rejected before environment construction.

The minimal repair is to use the exact manifest operation already used by the
successful replay gates:

```python
hashlib.sha256(initial.tobytes()).hexdigest()
```

No state bytes, entry, seed, model, action, branch, label, horizon, contract,
threshold, or budget changes are proposed. Before any retry, a CPU preflight
must verify this equality for all 16 registered entries and freeze the result.
The invalid `NO_IDENTIFIABLE_SIGNAL` marker from Retry 1 remains preserved but
must not be interpreted scientifically because zero groups reached an
intervention boundary.
