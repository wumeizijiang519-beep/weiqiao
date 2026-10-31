# Alternate verified-owned resource route; no further Slurm binding retries

Freeze Slurmparallel route after22FAILED41:0/0s and23pre-model binding failure.
23exposes CUDA_VISIBLE_DEVICES=0 while first21occupies nodeNVMLGPU0 and
SLURM_STEP_GPUS=4; scheduler binding does not map safely to inspected physical
ordinals. Guards refused before model initialization. Keep both failures and
all source/reg/log evidence; do not repeat these Slurm binding attempts.

Use previously verified owned1598338step_extern cgroup on gpu22, which passed
both physicalGPU kernel checks. FreshNVML confirms first21ownsGPU0/GPU1idle.
Explicit physicalGPU+UUID+UID+job/cgroup+idle checks remain mandatory and are
NOT relaxed. Export exact UUID to CUDA, not ambiguous scheduler ordinal. At
most2workers total including first21,4threads each within16CPU/60GB parent.
Do not touch first21or other users. This route uses the already allocated job,
not unallocated GPUs and NOT invented exclusive Slurmsteps.

Run exactly8unused fixed registrations already frozen in retry1registry;
they have never initialized a model. Source/seed/fold/update/corpus unchanged.
No completed fit re-run. One separately registered extern dispatcher/route,
no automatic further route retries. Wrong/busy/cgroup failure stops, never
selects alternative scientific seeds. Firstfit timing forecast still applies.

Charge each extern worker measured oneGPU wallclock incl failures; retain PID,
cgroup,UUID,start/end/exit/source and SSH transport exit separately. First21and
Slurm22/23use actualsacctGPUtime; parent allocation reservation hours separate.
All science/cost/reserve/deadline gates unchanged. After all9fixedfits complete,
independent OOF audit required; no automatic finalrefit/deployment.
