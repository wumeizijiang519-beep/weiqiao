# Progress-Pairwise QGF V1 Status

## 2026-10-28 00:16 CST - Pairwise critic stopped negative

- The user authorized direct training. Twelve fixed workers (three seeds by
  four physical-group-disjoint folds) completed cleanly on two allocated gpu22
  A800s. Slurm step `1598338.41` completed `0:0` in 482 seconds, charging 964
  allocated GPU seconds; all workers reached exactly 3,000 updates.
- The independent OOF qualification status is
  `NO_STABLE_PROGRESS_PAIRWISE_CRITIC`; REPORT SHA:
  `cedc63d8744ab298e211b55ce962f1684206c759536526bd52aa7aaee6573130`.
- Action-aware group-equal accuracies were `0.5536/0.5663/0.5510`. They beat
  state-only (`0.5`) for all seeds, but seed `202641601` lost to the matched
  within-group permutation control (`0.5969`). The other permutation controls
  scored `0.5204/0.4872`.
- Group-bootstrap confidence intervals crossed zero for both action-aware
  minus state-only (`[-0.0587, 0.1650]`) and action-aware minus permutation
  (`[-0.0986, 0.1378]`). Action sensitivity was 1.0 for all seeds, but the
  preregistered stability and control gates failed.
- No extra seeds, updates, folds, groups or thresholds are permitted. The
  critic is not released and no held-out online QGF validation is authorized.

## 2026-10-27 23:57 CST - Population signal gate admitted

- Resume step `1593640.401` completed cleanly (`0:0`) in 6,238 allocated GPU
  seconds. Together with the 754-second pilot and the preserved 1,442-second
  failed orchestration attempt, the population diagnostic used 8,434 GPU
  seconds, below the frozen 14,400-second cap.
- Fourteen of sixteen fixed physical groups completed, producing 112 real N8
  branches. Entries 3 and 5 were fail-closed because their reconstructed
  boundary observations did not match the archive; neither was retried or
  replaced.
- The frozen finalizer reports `PROGRESS_PAIRWISE_ACTION_VALUE_SIGNAL_ADMIT`.
  Binary discordance did not pass, but the preregistered continuous-progress
  gate passed in three task families at both horizons 16 and 32.
- Final REPORT SHA:
  `501d7ce97068100eec28aa1db070d70680411e14e223be9058919b2cc508f1b6`.
  The independent audit passed with zero errors; audit REPORT SHA:
  `d365e4a24d174eaeb329e0871464e7f32a0d60687f59a23dcb97aa11f234ae0d`.
- This result admits a separately preregistered pairwise action-critic study.
  It is not an online QGF efficacy result and does not authorize a positive
  QGF claim.

- The prospective 16-group cohort and four family-specific action-support PCA
  bases are frozen. The new groups do not overlap Failure-Critical Boundary V1.
- Runtime inventory step `1593640.396` failed after 114 allocated GPU seconds
  before WAM or robot actions because `njoint` should have been `njnt`.
- The user authorized the source-frozen minimal repair. Step `1593640.398`
  completed cleanly in 202 seconds with zero WAM calls and zero actions. It
  froze unambiguous bodies, target sites and articulation joints for all four
  families; REPORT SHA is
  `454a246375b48d6eaad89cdba77870ef08ca3953407e6d9d06856c2f89611a25`.
- The independent simulator-only continuous progress contract passed; REPORT
  SHA is
  `7507758f4ea8d1599579a58561c0acc26d1efcb464b06ef44c340fe5b78002a7`.
- The fixed entry-0 pilot runner, N8 candidate constructor, authorization,
  wrapper and independent auditor are source-hash frozen. Seventeen CPU tests
  pass. A minimal infrastructure retry may proceed without another user prompt
  only if every scientific input and threshold remains byte-identical and the
  failed cost remains charged; scientific gate failures remain final.
- Pilot step `1593640.399` completed `0:0` in 754 allocated GPU seconds. All
  eight candidates were unique and executed 32 real steps with zero candidate0
  replay and commit error. The independent audit passed; runner REPORT SHA is
  `285f6db92a6651d482e4e2aa2b1b2659fdf5b2662a83b5dae900865e46a85578`
  and audit REPORT SHA is
  `07d149c3a469b9f719fed33bc4e177de15c4ca69465cab01d8af1b2d0906ad40`.
  All candidates remained unsuccessful; their step-32 progress values ranged
  from about 0.2915 to 0.2972. This releases the population diagnostic but is
  not itself stable signal or QGF efficacy.
- Remaining step `1593640.400` completed entries 1 and 2, then failed closed at
  entry 3 because its reconstructed policy observation differed from the
  archived boundary. It consumed 1,442 GPU seconds. Entry 3 is unavailable and
  is neither retried nor replaced; its failure receipt is frozen.
- The single authorized orchestration repair is active as step `1593640.401`.
  It starts at entry 4, preserves the scientific runner byte-for-byte, and may
  continue past only the same exact boundary-observation mismatch. Any other
  failure stops. Its 12,180-second timeout keeps pilot, failed step and resume
  within the original 14,400-second cap. No further automatic retry is allowed.
- The independent full-population finalizer and artifact auditor are now
  source-frozen before remaining outcomes exist. Nineteen CPU tests pass.
  Bootstrap uses seed 202641501 and 10,000 physical-group draws per
  family/horizon; these values cannot be changed after observing results.
- No Progress-Pairwise QGF online result exists yet.
