# Resource audit interpretation and stop

CPU comparison exited2 with NUMERIC_PORTABILITY_FAILED. Original Stage0 native
actions differ by up to0.003662109375; normalized actions up to0.0078125;
support basis differs0.09091673046. All exceed frozen1e-6 portability tolerance.
Original gpu4 ENGINEERING_PASS only proves internal repeats, not cross-node
parity. Freeze gpu4 WAM portability for this configuration. Do not relax the
tolerance, choose favorable arrays/seeds, call it qualified or rerun GPU work.
No robot action or new cohort episode was executed by these checks.

CPU_PORTABILITY_AUDIT.json mistakenly sets cpu_auditor_clean_exit=true even on
its explicit SystemExit(2) failure path. The actual command exit2 and FAILED
status are authoritative; that boolean is incorrect and must not be used for
admission. Preserve the original report/source rather than overwriting evidence.
This erratum is not a PASS or permission for another resource attempt.

Integration cost is1058Stage0+7+3+55+673resource=1796GPU seconds. CPU comparison
adds0GPU seconds. resource_cost_supplement.py freezes all four attempt hashes
and charges failures; consumers add only738resource seconds to existing Slurm
totals, not1796which would count Stage0 twice. Frozen aggregate_training_v2.py
continues to certify its original Slurm cost scope; include this supplement in
all admission budget checks, encoder/critic registrations and final cost tables.

Current collector remains original gpu1, last shard3. gpu22 kernel qualification
still valid for small independent critics after data/encoder qualification.
Do not let this resource stop reopen old science configurations or disturb
gpu4 GPU0/2 actors. gpu1 allocation expires October29 15:50CST; forecast every
downstream stage against both allocation expiry and platform deadline.
