# User-approved runtime inventory retry2

Authorization: user replied "批准" on2026-10-27 after being told that steps348
and351 exhausted the prior retry allowance. This authorizes exactly one retry2
for the corrected import order, not paired actions or WAM loading.

Preserve steps348/351 and their115/108 allocated-GPU seconds. Retry2 uses the
same first fixed metadata entry, zero WAM/model/dummy/robot actions,2CPU/8GB,
one allocated idle gpu1 GPU0, inner240seconds and Slurm5minutes. It writes only
runtime_inventory_retry2. Source and command hashes are frozen before launch.
Success means runtime object inventory only; it is not snapshot restoration,
A-B-A replay, candidate comparison or QGF evidence. Any retry2 failure stops
runtime inventory with no automatic retry.
