# UniWAM Release Gate V1

## Scope

UniWAM is the B4 fallback after LiLa-WAM failed the source-license gate. This stage is
CPU/network only until the complete release matrix is verified.

## Frozen source

- Official repository: `UniWAM/UniWAM`.
- Commit: `8dcd3401bccda8c002fc558e356b975b1789eecd`.
- Source license: Apache-2.0, to be verified against the archived `LICENSE` file.
- Official benchmark paths: RoboTwin deployment and LIBERO-Plus evaluation are present.
- Advertised RoboTwin checkpoint: `Kosmos524/UniWAM-robotwin-clean`.

## Release checks

1. Freeze source archive SHA256 and verify license and official adapter paths.
2. Freeze checkpoint repository revision, all file sizes/SHA256 values, and model license.
3. Inventory Qwen3-VL-2B and Wan2.2-TI2V-5B dependencies, reusing only byte-identical
   assets already verified under `pqr`.
   The official RoboTwin loader specifically requires native
   `Wan2.2_VAE.pth`, `models_t5_umt5-xxl-enc-bf16.pth`, and the
   `google/umt5-xxl` tokenizer tree. DiffSynth `.safetensors` variants are not
   considered interchangeable and must not be converted or renamed to pass
   this gate.
4. Record action dimension, normalization, camera order, horizon/replan, policy memory,
   explicit candidate seed support, expected VRAM, and host ABI/runtime constraints.
5. If any required public artifact or executable adapter is absent, freeze a blocker and
   stop before GPU use. Otherwise, pre-register one strict model-load smoke.

