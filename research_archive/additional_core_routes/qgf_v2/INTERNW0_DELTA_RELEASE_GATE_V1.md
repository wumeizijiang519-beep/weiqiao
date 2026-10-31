# InternW0-Delta Release Gate V1

Frozen: 2026-10-25 07:48 CST

## Official source

- Repository: `InternRobotics/InternW0-Delta`.
- Source commit: `90801baa3bdc7829c1e4989edfe3d0fb2410ea6a`.
- GitHub source archive SHA256: `9e1083e7426e8ee67fe82c5d6b92356de62837bd0320aacba9ce81cbdba3b8e7`.
- Repository license: MIT, with third-party notices retained under `LICENSES/`.

The login-node Git client is too old for partial clone and direct GitHub HTTPS timed out. The same official `main` commit archive was fetched through the local network and uploaded unchanged. This is an infrastructure transport substitution only.

## Public task checkpoints

| Task | Hugging Face revision | File | Bytes | LFS SHA256 | Model-card license |
| --- | --- | --- | ---: | --- | --- |
| LIBERO | `00524e29e160b2f092bf6c5a47e325301a31fb90` | `libero.pt` | 12,423,419,478 | `8484e70ac0188edaf3d014a2ebb49666415356aa6ccb21feb8ace27abcc55466` | Apache-2.0 |
| RoboTwin | `ee034358829ac834a82bf5ef6a61a67d9c2211bc` | `robotwin.pt` | 12,423,419,613 | `72517a2a5799f35e10d770c3f8bbee05ddc02916be0c14400872ee79cfc5b211` | Apache-2.0 |

Both repositories are public and ungated. Download the LIBERO checkpoint first. Do not download the RoboTwin checkpoint until the LIBERO release/parity path is executable or a separate storage budget is recorded.

The LIBERO checkpoint is complete under `checkpoints/InternW0-Delta/libero.pt`: exact byte count and SHA256 match the table above. Verification evidence is frozen in `runs/internw0_delta_libero_ckpt_v1/VERIFY.txt` and `ASSET_COMPLETE`.

## Frozen backbone assets

| Component | Repository revision | File(s) | Total bytes | SHA256 status |
| --- | --- | --- | ---: | --- |
| Wan2.2 TI2V diffusion | `Wan-AI/Wan2.2-TI2V-5B@921dbaf3f1674a56f47e83fb80a34bac8a8f203e` | three `diffusion_pytorch_model-*.safetensors` shards | 19,999,234,384 | Per-file values frozen in `runs/internw0_delta_backbone_assets_v1/MANIFEST.tsv` |
| Converted UMT5 encoder | `DiffSynth-Studio/Wan-Series-Converted-Safetensors@150f75d811d51f6c7760154aa7fec371dccda529` | `models_t5_umt5-xxl-enc-bf16.safetensors` | 11,361,845,432 | `d92de679881d38af9c89eff7bb1b6d6c9d96cb2b69831e4027e9ecabdd38eb23` |
| Converted Wan2.2 VAE | same revision | `Wan2.2_VAE.safetensors` | 1,409,401,152 | `0e913a2ca571c75fcb63385a8edadcca73454af5842596cb1ad11e4142590996` |
| UMT5 tokenizer | `Wan-AI/Wan2.1-T2V-1.3B@37ec512624d61f7aa208f7ea8140a131f93afc9a` | official `google/umt5-xxl/` files | 21,385,730 plus metadata | Large-file hashes frozen in the manifest; all final files will be hashed |
| RynnBrain VLM | `Alibaba-DAMO-Academy/RynnBrain1.1-2B@36069aa841fc58f500d307316cbfdf379777ce8a` | model, processor and tokenizer files | 4,446,548,207 plus metadata | Large-file hashes frozen in the manifest; all final files will be hashed |

The DiffSynth Hugging Face endpoint did not expose the files through the available mirror. The project's official ModelScope repository does: its immutable latest commit, exact byte sizes, and SHA256 values were retrieved from the ModelScope repository API. This is the exact repository and filenames named by the official InternW0-Delta loader, not a substitute model.

All three CPU/network-only groups completed. Every large file matches its frozen byte count and SHA256; small files are pinned by repository revision and have a complete local SHA256 inventory. Evidence is frozen in `runs/internw0_delta_backbone_assets_v1/{MANIFEST.tsv,VERIFY.tsv,SMALL_FILES_SHA256SUMS,ASSETS_COMPLETE}`. No GPU was used for acquisition or verification.

## Official adapters and action contract

- LIBERO-Plus: `eval/libero_plus/README.md` and `python -m eval.libero_plus.run_libero_plus`.
- RoboTwin 2.0: `eval/robotwin/README.md` and `python -m eval.robotwin.run_robotwin`.
- LIBERO cameras: agent and wrist RGB, each resized to `192x256`, vertically concatenated for the video path and retained separately for the VLM.
- Native benchmark action: 7D. The official processor maps it into the canonical 80D right-arm slots `[47,53)` plus gripper slot `[56,57)`, then denormalizes back to 7D for execution.
- LIBERO action horizon: 32; replan interval: 10; binary gripper enabled.
- Official normalization: `assets/stats/libero.json` with min/max mode.
- Server memory: per-client AR/memory state is explicit in `OnlinePolicySession`; prompt context and action/visual/proprio histories are session-local.
- Candidate control: diffusion noise is generated on CPU and the inference function accepts an explicit seed. The session also stores a private CPU RNG state. A same-observation N4 adapter must snapshot all session memory, generate four fixed-seed candidates, and commit only the selected branch.

## Runtime and remaining gates

- Required Python: 3.10-3.13; official stack pins Torch 2.10.0/CUDA 12.8, torchvision 0.25.0, Transformers 5.13.0, and Hugging Face Hub 1.21.0.
- The first isolated runtime attempt failed dependency resolution before installation: the cluster's glibc 2.17 cannot load Torch 2.10's available manylinux 2.28 wheels. The allocated A800 nodes also expose driver 535/CUDA 12.2, which cannot support the pinned CUDA 12.8 runtime. This infrastructure failure is retained in `runs/internw0_delta_runtime_v1`.
- A separately named compatibility probe keeps Python 3.10 and every non-Torch project pin, including Transformers 5.13.0, but uses Torch 2.6.0+cu124 and torchvision 0.21.0: the newest stack already demonstrated on these nodes. It is only a release-gate probe; import and strict model-load parity must pass before it can be admitted, and the runtime deviation must remain disclosed.
- Its first installer attempt was blocked before installation because `download.pytorch.org` timed out. Retry2 makes no package-version change: it hard-link clones the already verified local Kairos cu124 environment into a new isolated path, upgrades the non-Torch pins there, installs InternW0 without dependency re-resolution, and verifies that the source Kairos environment's package freeze is unchanged.
- Retry2 then stopped before installation because the official `torchcodec==0.10` wheel requires manylinux/glibc 2.28. Source audit found `torchcodec` only in dataset video decoding; the unchanged official code explicitly falls back to PyAV when it is absent, while the online LIBERO policy does not import it. Retry3 therefore omitted only this unavailable optional backend and required an explicit PyAV fallback plus online-policy import audit.
- Retry3 reached the next packaging stage but failed while setuptools staged `robomimic==0.2.0` metadata in the shared uv cache with `Directory not empty`; no package, model, or GPU action completed. Retry4 preserves all versions and assertions from retry3 and changes only uv's build cache to a unique login-node-local `/tmp` directory. It remains a disclosed compatibility probe until CPU import and strict official model loading both pass.
- Retry4 moved the build cache successfully and exposed a separate official metadata conflict: the project advertises Python 3.10 support while its pinned eval dependency `scikit-image==0.26.0` requires Python 3.11 or newer. Retry5 moved to the already installed Python 3.12.7, which is inside the project's supported range, without downgrading any non-Torch pin; it then confirmed the shared-filesystem staging race also affects `bddl`.
- Retry6 keeps retry5's Python, versions, source, and import assertions but puts the complete uv cache and all sdist builds in a unique node-local `/tmp` directory. Resolution succeeded for 126 packages and the pinned source builds are active; no GPU or model result is claimed until `RUNTIME_COMPLETE` and the strict model-load gate exist.
- Retry6 proved the local build path works (`bddl` and other sdists built), but pinned `pyarrow==24.0.0` has no glibc-2.17/Python-3.12 wheel and its source build dependency `libcst` required an unavailable Rust toolchain; a full official development runtime is therefore blocked on this host ABI. The final retry7 is explicitly inference-only: it returns to the proven Python-3.10/Torch-2.6 base, keeps official model-path pins and `datasets==3.6.0`, reuses imported `pyarrow==18.1.0`, and omits off-path training/simulator pins. This is admissible only if CPU imports, strict checkpoint loading with zero missing/unexpected tensors, and official closed-loop parity all pass; otherwise InternW0 is frozen.
- Required backbones: Wan2.2-TI2V-5B diffusion files, converted Wan2.2 VAE and UMT5 encoder, Wan2.1 UMT5 tokenizer files, and RynnBrain1.1-2B. The Rynn model has a ModelScope fallback.
- The 12.4 GB task checkpoint plus a 5B video model and 2B VLM should fit an 80 GB A800 in principle, but this is only an estimate. Measured model-load VRAM is mandatory before admission.
- No GPU work before the LIBERO checkpoint and all required backbone files have immutable revisions and SHA256 records.
- After assets: isolated import/model-load smoke, one official baseline episode, then same-observation N4 contract/diversity and exact memory-restore audit.

The final inference-only retry failed before model import because the pinned
`av==16.0.1` source build requires FFmpeg development libraries absent from the
cluster. Per the frozen final-retry rule, no older Av, stub, or further runtime
substitution is admitted. All assets and failures remain retained.

Status: `BLOCKED_HOST_ABI_AND_BUILD_DEPS`; no GPU model-load or QGF evidence
exists. The route is frozen and B2 Simple-WAM is promoted.
