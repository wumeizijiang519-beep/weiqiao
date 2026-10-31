# UniWAM Model-Load Smoke V1

## Purpose

Validate the frozen official UniWAM RoboTwin-clean checkpoint in the single
disclosed Torch 2.6/cu124 inference-only compatibility runtime. This is a
release gate, not QGF evidence.

## Frozen Inputs

- Source commit: `8dcd3401bccda8c002fc558e356b975b1789eecd`.
- Checkpoint repository revision: `f174cc20f0b4e84d5c80831ae746a9fb4c55d515`.
- Checkpoint SHA256:
  `66055df4d9a8a50cd84a45147e4e268ab96cfbe2c47c2aeadc9e9bc7880a1df2`.
- Combined asset manifest SHA256:
  `b332ea82c79cb369017a44aa8a3dce4a5292136a562923d86a3fcb0c3f12d63f`.
- Model config: official `robotwin_lap_history_flow_clean.yaml`.
- Inference mode: `history_flow`, four denoising steps, history action noise
  `0.02`, future-video denoise fraction `1.0`.
- Runtime: isolated Python 3.10 overlay with official Transformers 5.0.0rc0,
  Torch 2.6.0+cu124 compatibility base and validated GCC11 runtime libraries.

## Resources And Limit

- One explicitly allocated, initially idle A800.
- Eight CPUs and at most 45 GiB host RAM.
- Hard limit: 45 wall-minutes / 0.75 GPU-hours.
- No simulator, action generation, reward, or episode is run.

## Admission

PASS requires the complete official policy constructor to load the native Wan
VAE/T5 tokenizer assets, Qwen processor, and the full task checkpoint, with
checkpoint log counts `missing=0` and `unexpected=0`. Record parameter count,
peak CUDA bytes, wall time, device, software versions, all frozen asset hashes,
and the complete log. Any weight mismatch, OOM, semantic/runtime exception, or
timeout freezes this compatibility route; no model-code or checkpoint patch is
allowed.
