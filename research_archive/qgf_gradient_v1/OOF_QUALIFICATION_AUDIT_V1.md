# Independent complete-nine OOF qualification audit

This freezes implementation of existing PROTOCOL offline gate before reading
any partial worker MSE. No current seed/fold result is used to revise criteria.
All9fits/processes/dispatcher must be clean and final20000; verify registration,
checkpoint,normalizer,split/bootstrap/permutation stream,raw prediction targets
and complete exact per-seed held episode union. Normalizer independently
recomputed from training-fold observations only (atol1e-7/rtol1e-6); no heldout
labels enter it. Actual MCtarget must match certified corpus exactly. Shared
heldTD and reported per-episode errors are independently recomputed and matched.

All3bootstrap seeds must actionMSE<same-targetstate-only ANDactionMSE<within-bank
permutation control AND action-modelpermutation raises error. Pool model-seed
errors within each episode BEFORE physical-group bootstrap10000draws with fixed
seed202640901. Allthree improvement interval lowerbounds>0 required. Intervals
are marginal95percent percentile group intervals, not simultaneous bounds or
independent-model-scene inference. These are necessary offline screens,not causal
same-state proof and not online efficacy. Fixed10unit-interval calibration bins
(out-of-range assigned edge,unclipped means/errors) and MC/prevalence descriptive
diagnostics do not add posthoc admission thresholds.

qualify_rl_oof.py outputs immutable OOF_QUALIFICATION_RESULT.json/SHA only after
full audit. PASSauthorizes only fixed3all-training refits,not onlineuse directly.
NO_STABLE_EXECUTION_ALIGNED_ACTION_VALUE_EVIDENCE freezes this config; no seed/
fold/updates/hyperparameter retuning or finalrefit/online. Auditinfra failure is
separate from negative science and preserves artifacts. No result overwrite.
ActualfirstSlurm21,failed22/23whole-second costs and externGPUelapsed are all
included; parentallocationreservationhours separate,phase8GPUh20percentreserve.

CPUaudit source/tests/actualcorpus SHA must be registered before dispatch.
No partial performance gate, no automatic repeated training. Five syntheticgate/
calibration tests plus existingmetrics tests prepare code only,notmethod evidence.
