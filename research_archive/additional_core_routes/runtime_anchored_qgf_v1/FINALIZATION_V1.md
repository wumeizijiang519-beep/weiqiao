# Runtime-Anchored Finalization V1

The finalizer combines exactly the independently audited pilot (entry 0), the
ten clean pre-interruption groups (entries 1-10), and the clean fixed-index
resume (entry 11). Entries 12-15 are recorded as not executed by the stopping
rule frozen before the resumed outcome. Statistics use bootstrap seed
202642201 and 10,000 physical-group draws. A separate implementation verifies
all 96 real branch artifacts and independently recomputes admission metrics.
