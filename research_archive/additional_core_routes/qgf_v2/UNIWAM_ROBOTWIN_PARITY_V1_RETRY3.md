# UniWAM RoboTwin Parity V1 Retry 3

- Parent retry2 reached the first real policy inference call and failed before
  executing an action because the deployed policy had been packaged
  incorrectly.
- The deployment first copied the complete official
  `inference/robotwin/uniwam` bundle, then mistakenly overwrote its bundled
  `models/` and `utils/` with repository-top-level training modules. The
  overwritten training `Motus.inference_step` lacks the deployment argument
  `future_video_denoise_fraction`; the official bundled implementation accepts
  it and is the implementation referenced by the deployment README.
- This retry restores the official policy bundle byte-for-byte from the pinned
  source commit. It does not patch model semantics or change any scientific
  setting. The deployed/source tree hashes and a diff audit are frozen before
  launch.
- GCC11, single-task Slurm execution and pinned ffmpeg remain unchanged. Task,
  seed, checkpoint, assets, observations, actions, reward, success criterion,
  and 60-minute/1-GPU-hour ceiling remain identical.
