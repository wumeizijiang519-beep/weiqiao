# Checkpoint Recovery V3

User repair authorization: 2026-10-26, "repair". Audio remains disabled.
This is a new explicit checkpoint-restoration contract, not a retroactive V2 pass.

V2 incorrectly required recomputation of every historical raster from physical
state and actions alone. Two diagnostic reconstructions first differed at
boundaries 6 and 8 despite exact preceding simulator states. Official image
resize retains unequal pixels. Do not mask pixels, round images, change camera
settings, enlarge a tolerance, or claim bitwise raster regeneration.

Restore the actual retained sensor snapshot alongside the reconstructed physical
and RNG state, as a checkpoint component. Use only the original measured image,
never a synthetic observation. Audit every archived physical state and real
reward/done/success, non-image sensor, selection sequence, caller RNG, and two
independent controller-history traces. Restore observation_0021 exactly for the
first resumed policy input. Subsequent environment observations remain live and
unaltered. Record every historical raster mismatch separately, without hiding it.
No policy inference or new action is performed in this recovery gate; archived
actions are replayed only to reconstruct the same partial episode. No completed
episode is resampled or relabelled. No reward is added for unexecuted candidates.

Admission requires two complete 210-action reconstructions, exact archived
physical states/feedback/proprio/RNG/selection, equal controller traces, and exact
retained observation restoration. Any physical/feedback/proprio/RNG/controller
failure stops recovery. Raw rendering equality is a separately reported property,
not a claim of this checkpoint contract. This distinction must remain disclosed.

Budget: two render diagnostics (92s failed + 29s completed), then one bounded
two-reconstruction gate, hard 10 minutes / 0.1667 GPUh on one allocated A800.
All costs count toward the existing collection cap; no budget increase.
Do not resume collection until this report has been independently checked.
