# UniWAM RoboTwin Parity V1

## Scope

One official RoboTwin 2.0 baseline episode for the released
`UniWAM-robotwin-clean` checkpoint. This is a release/parity gate only and is
not QGF evidence.

## Frozen setting

- Task: `lift_pot`.
- RoboTwin config: `demo_clean`.
- Evaluator seed: `10000`.
- Episodes: `1` accepted expert-feasible initial state.
- Instruction split: `unseen`.
- Inference mode: `history_flow`.
- Diffusion steps: `4`.
- Action-history noise standard deviation: `0.02`.
- Future-video denoise fraction: `1.0`.
- Checkpoint, Wan2.2 and Qwen3-VL assets are exactly those admitted by
  `UNIWAM_RELEASE_GATE_V1.md` and the model-load smoke.

The upstream evaluator hard-codes `test_num=100` after parsing its CLI. A
run-local evaluator copy changes only that assignment to
`int(usr_args.get("test_num", 100))`, restoring the documented CLI contract.
The before/after diff and hashes are evidence. No model, observation, action,
reward, success criterion, task, or seed is changed.

## Admission

- The official simulator and policy complete one accepted episode.
- Result and video artifacts exist and are hashed.
- The log contains the final `Success rate` line and no policy/simulator error.
- Report success, environment steps, wall time, peak VRAM, and hashes whether
  the episode succeeds or fails. Episode outcome does not affect parity
  admission when the full closed loop is valid.

## Budget

- One explicitly allocated A800 and 8 CPUs.
- Expected 15-30 minutes; hard limit 60 minutes and 1 GPU-hour.
