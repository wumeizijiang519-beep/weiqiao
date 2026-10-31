# One bounded feature-device alignment repair

Encoder337FAILED1:0/439GPU seconds. Actual unchanged WAM strict load passed;
first current-only feature concatenation failed because official text encoder
offload returns CPU text context while VAE vision is CUDA. No complete feature
audit/critic/data block exists. Source/report/FAILED/step and439s are preserved.
The first pilot continuation correctly stopped1 without launching a GPU pilot.

Minimal features.py repair leaves text masked pooling on its original device,
then transfers the pooled float32 vector and float32 proprio to vision.device;
remaining-time scalar is created on vision.device. Values, masks, feature order,
pool size, model/dtype/checkpoint/source, camera, episode endpoints, seed,
success criteria and1e-6A-B-A tolerance unchanged. No observations/rewards altered.
Original code preserved as features_before_device_fix.py (SHA54bb...0bb4a).

One new run encoder_audit_v1_retry1, same8CPU/45GB/GPU0/22minSlurm/1200sinner,
after337finished and GPU freed. New registered source SHA before retry. CPU
feature tests must pass first; actual GPU A-B-A remains authoritative. No
automatic further encoder retry if this fails; preserve and audit first cause.
No GPU4 portability restart. CPU device transfers are not a new critic/model.

Failed439s count in feature/critic8GPUh cap and cumulative total, keep20percent
reserve. Pre-retry completed total34710+439=35149GPU seconds. Any new pilot
controller must target the new exactstep/control/source hashes; never restart
the stopped337controller with changed code or erase its failure.
