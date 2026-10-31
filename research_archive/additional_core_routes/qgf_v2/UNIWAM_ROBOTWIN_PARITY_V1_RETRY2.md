# UniWAM RoboTwin Parity V1 Retry 2

- Parent retry1 reached official model initialization, loaded the checkpoint,
  created an expert-feasible task state, and then failed before the first
  policy action because `ffmpeg` was absent.
- The parent produced no executed model action and is retained as an
  infrastructure failure, not a robot episode.
- This retry adds only a pinned static `ffmpeg` 7.0.2 executable from
  `imageio-ffmpeg==0.6.0` to `PATH`. The executable SHA256 is
  `e7e7fb30477f717e6f55f9180a70386c62677ef8a4d4d1a5d948f4098aa3eb99`.
- The validated GCC11 fix and `--ntasks=1` remain fixed. Model, checkpoint,
  assets, task, seed, observations, actions, reward, success criterion and
  60-minute/1-GPU-hour ceiling are unchanged.
