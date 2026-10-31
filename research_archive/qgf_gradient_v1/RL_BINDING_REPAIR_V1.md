# One bounded scheduler binding repair before fold1 model initialization

First real fit1598338.21 remains active and must not be repeated. Generic
fold1launcher22exited41before creating model/control directory because it treated
SLURM_STEP_GPUS as an NVML ordinal. Owned firstfit /proc environment proves
SLURM_STEP_GPUS=2 but CUDA_VISIBLE_DEVICES=0 on actual nodeGPU0. This cluster's
GRES indexes are offset.22FAILED41:0/ElapsedRaw0/oneGPU,0model updates/GPU seconds;
keep original dispatcher failure/log and pre-repair wrapper source.

Minimal correction uses CUDA_VISIBLE_DEVICES for the already inspected NVML
GPU0/1mapping, verifies expected UUID/idle before launching, then pins that UUID
for PyTorch. Print both scheduler bindings before validation. Source/seed/fold/
batch/critic/updates/targets unchanged. No foreign process signalled. Independent
GPU1 must be idle and owned; wrong/busy mapping still fails rather than retries.

One distinct remaining-eight dispatcher retry, same8predetermined registrations
and future scientific run directories, only parser/source manifest/controller
directory changed. Original firstfit not restarted, validfits not overwritten.
No automatic further binding retries. Remainingfit finalstep/OOFgate still fixed.
