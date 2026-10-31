# Critic Qualification Coverage Repair V1

The first zero-GPU qualifier stopped before producing a result because physical
group 7 has exactly identical horizon-32 progress for all eight candidates and
therefore no non-tie pair under the frozen `1e-6` tolerance. Training workers
and predictions are unchanged.

The repaired qualifier keeps all 12 groups in the scientific denominator. A
group without an evaluable pair receives zero improvement against both
controls and is listed as missing coverage. Admission additionally requires
12/12 informative group coverage, so this repair is conservative and cannot
turn missing evidence into a pass. The failed qualifier attempt is preserved.
