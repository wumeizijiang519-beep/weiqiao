# UniWAM RoboTwin Parity V1 Retry 4

- Retry3, exact step 1593640.302, failed after official model loading and
  expert-feasible environment initialization, at the first VAE Conv3d before
  any model action. The log reports failure to load
  libcudnn_engines_precompiled.so.9.5.1 (and its fallback names), followed by
  ptrDesc->finalize(). Slurm reports FAILED, 11:0, elapsed 00:07:06.
- The admitted Torch 2.6 base already contains libcudnn_engines_precompiled.so.9
  and its matching cuDNN libraries. This retry adds only that existing
  nvidia/cudnn/lib directory to LD_LIBRARY_PATH. No library is installed or
  replaced, and the official policy bundle remains byte-identical.
- Preserve retry3 logs, launcher, source-tree manifests and failure accounting.
  Freeze the launcher diff and its SHA before launch. First verify on the
  allocated node that the existing engine library can be dynamically loaded
  under the corrected environment without model execution.
- Task lift_pot/demo_clean, evaluator seed 10000, one accepted expert-feasible
  episode, unseen instruction, history_flow, four denoise steps, history
  noise 0.02, future-video fraction 1.0, checkpoint, assets, dtype, observations,
  actions, reward and official success criterion are unchanged.
- One assigned idle A800, 8 CPUs, 45 GB RAM; hard 60-minute/1-GPU-hour ceiling.
  This is still baseline parity, not QGF evidence. All failed-attempt resource
  costs remain separately reportable and are not erased by retrying.
