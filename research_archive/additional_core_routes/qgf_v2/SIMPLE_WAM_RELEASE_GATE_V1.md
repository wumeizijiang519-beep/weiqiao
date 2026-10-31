# Simple-WAM Release Gate V1

Frozen: 2026-10-25 09:47 CST

## Scope

This is the B2 fallback after the frozen InternW0-Delta host-ABI blocker. It is
a CPU/network-only release audit until source, task weights, benchmark assets,
license, action contract, candidate control, and resource estimates pass.

## Official source

- Repository: `LeapLabTHU/Simple-WAM`.
- Commit: `396cba18c318bc33a1ef42513b85298e3016e28a`.
- Source archive SHA256: `6b7814f4bec5b67221d754b3eadfd1421f2c295270c72c636d88389185807d1d`.
- Repository license: MIT; pinned `LICENSE` SHA256
  `8379dddfbbb1154ad9cc57f008f1f8d4a8d26c3de99bd6b36aa4d8067888aa92`.
- Official runtime: Python 3.10, Torch 2.7.1+cu128, torchvision 0.22.1+cu128.

The pinned source archive must be stored under `backbones/`, hashed, and
extracted without modification. A source transport retry does not change the
commit.

## Public release claims to verify

- Model repository: `rpzhou/Simple-WAM`.
- LIBERO checkpoint: `simplewam_checkpoints/libero_joint_2cam224_1e-4.pt`.
- Normalization: `simplewam_checkpoints/libero_dataset_stats.json`.
- Benchmark assets include `libero_plus.tar.gz` and `robotwin_assets.tar.gz`.
- The same released LIBERO checkpoint is used for LIBERO-Plus.
- Official LIBERO-Plus command uses one rollout per task variant, 10 inference
  steps, frozen future-video noise, action compilation, and text-encoder
  offload.
- Official RoboTwin evaluation supports both clean and randomized phases.

## Frozen LIBERO assets

- Model repository revision: `9329fdfed21a6ef0f32f91cfbedeb1969f794fe5`.
- Checkpoint: `simplewam_checkpoints/libero_joint_2cam224_1e-4.pt`,
  `12041735545` bytes, LFS SHA256
  `2b1e2f36ff06e701026028402976a4174be23ab48469289d01c93ce541b21d66`.
- LIBERO-Plus bundle: `benchmark_assets/libero_plus.tar.gz`,
  `6150336654` bytes, LFS SHA256
  `3bad55e3f195ee734fd24eebdcd47fee756255b604dffc2011b726f5a18381f8`.
- Dataset statistics: `simplewam_checkpoints/libero_dataset_stats.json`,
  `40959` bytes, SHA256
  `6b49b1bdf37268e3f1e6e621c4d5cb03ba028f3fabff3df3c68067c0a7c91c69`.
- RoboTwin weights and assets are deliberately deferred until LIBERO is
  executable, avoiding about 27 GB of non-critical-path storage.

## Audited LIBERO contract

- Primary camera is concatenated before wrist camera, horizontally; each is
  center-crop resized to `224x224`, producing an input of `224x448`.
- Native action is 7D: six delta end-effector coordinates and one absolute
  gripper coordinate. Dataset normalization is min/max; inference denormalizes
  before the official gripper sign conversion and optional binary sign.
- State is 8D; action horizon is `33 - 1 = 32`; frozen evaluator replan is 10.
- `infer_action` accepts an explicit seed and creates a CPU `torch.Generator`;
  candidate sampling can therefore use explicit native seeds without decoded
  action perturbation. The online evaluator otherwise reuses `cfg.seed` at
  every replan and the model path is stateless; candidate0 replay is still a
  mandatory empirical gate.
- LIBERO-Plus evaluation freezes future-video noise and uses 10 inference
  steps. All N4 methods must use the same native candidate interface and cost.

## Frozen backbone reuse

`DIFFSYNTH_MODEL_BASE_PATH` can point at the existing global checkpoint root;
the official Simple-WAM loader resolves exactly the following already verified
InternW0 assets, without copying or conversion:

- Wan2.2 TI2V diffusion shards SHA256: `720b06c4...`, `09ec5ef7...`,
  `6306f789...`.
- Redirected UMT5 encoder SHA256: `d92de679...`.
- Redirected Wan2.2 VAE SHA256: `0e913a2c...`.
- Wan2.1 UMT5 tokenizer `spiece.model`/`tokenizer.json` SHA256:
  `e3909a67...` / `6e197b4d...`.

The loader's registry hashes and strict task-checkpoint accounting still must
pass in the isolated runtime; prior asset verification is not model parity.

## Admission sequence

1. Freeze source archive SHA, LICENSE, requirements, and checkpoint inventory.
2. Freeze exact checkpoint/assets revisions, byte counts, SHA256, and license.
3. Audit native action dimension, normalization, two-camera order, action
   horizon/replan, RNG/future-noise controls, and model memory.
4. Estimate model-load VRAM against one 80 GB A800. No GPU before steps 1-3.
5. Import/model-load smoke with strict checkpoint accounting.
6. One official LIBERO-Plus parity episode.
7. Same-observation N4 contract, diversity, candidate0 replay, and memory/RNG
   restore audit.

Only after all gates pass may a training-only randomized intervention pilot be
pre-registered. No existing UNITAS, OpenWAM, ImageWAM, Kairos, or InternW0
critic/result is transferred.

The three LIBERO artifacts completed exact byte/SHA verification in
`runs/simple_wam_assets_v1_retry1/ASSETS_COMPLETE`. The first launcher failed
before any payload write due only to shell local-variable initialization and is
retained separately.

## Runtime gate

- Official Torch 2.7.1/cu128 is incompatible with the allocated driver 535.
- The disclosed compatibility runtime uses the already verified Torch
  2.6.0+cu124 and torchvision 0.21.0+cu124 base, while preserving official
  Simple-WAM source, Transformers 4.49.0, checkpoint, assets and dtype.
- Training/data/video-only packages are omitted. Top-level official imports
  require Hydra/ANTLR, boto3 and GitPython; their pinned packages are present.
- `runs/simplewam_runtime_v1_retry6/RUNTIME_COMPLETE` proves CPU import of the
  official runtime, FastWAMJoint and processor, plus exact resolution of all
  frozen backbone paths. Runtime freeze SHA256 is `d27d7c46...`; import report
  SHA256 is `d984e714...`. The inherited base freeze is unchanged.
- Earlier resolver, shared-temp, venv-path and missing top-level dependency
  failures remain separately retained and contain no model execution.

## Strict model-load gate

- `runs/simplewam_model_load_v1/MODEL_LOAD_COMPLETE` freezes a PASS from the
  unchanged official `sim_libero` BF16 loader on job `1593640` GPU0.
- The frozen checkpoint matched its expected byte count and SHA256. The model
  contains `12,406,309,603` parameters; MoT loading reported zero missing and
  zero unexpected keys, and the proprio checkpoint loaded strictly.
- Construction, checkpoint loading, and CUDA transfer took 159.149 s, 4.829 s,
  and 5.898 s respectively (184.903 s total). Peak allocated CUDA memory was
  `24,839,529,984` bytes on an A800 80GB.
- Both allocated GPUs were verified idle after completion. This is a release
  gate only, not baseline performance or QGF evidence.

## LIBERO-Plus runtime gate

- The frozen archive was extracted into the official
  `third_party/LIBERO-plus` layout and the package installed without changing
  benchmark source.
- The first import exposed omitted simulator dependencies because the official
  LIBERO-Plus package declares an empty `install_requires`. Failed retries are
  preserved. The isolated runtime now records official `robosuite==1.4.0`,
  `bddl==1.0.1`, `mujoco==2.3.7`, and the minimum numeric/image dependencies.
- Official `av==16.0.1` has no glibc-2.17 wheel and cannot build without host
  FFmpeg development libraries. The disclosed inference-only compatibility
  runtime uses the latest available manylinux2014 wheel, `av==14.2.0`, only for
  rollout-video encoding; model, observations, actions, reward, and success
  evaluation are unchanged.
- `runs/simplewam_libero_plus_env_v1_retry8/ENV_COMPLETE` freezes an import
  PASS on the allocated gpu1 node for LIBERO-Plus, robosuite, BDDL,
  scikit-image, and Wand.

## Parity infrastructure retry

- The first parity attempt completed strict model load and simulator creation,
  then reached the first real model replan after 30 official dummy wait steps.
  TorchInductor's Triton driver used system GCC 4.8 and failed to compile
  `stdatomic.h`; no model action was executed. The complete traceback and
  partial video directory are retained under
  `runs/simplewam_libero_plus_parity_v1` as infrastructure failure evidence.
- `runs/simplewam_triton_gcc11_patch_v1` freezes the only retry change: runtime
  `CC`, `CXX`, and `CUDAHOSTCXX` now point to the already validated isolated
  GCC/G++ 11.4 toolchain, with its library path and a fresh run-local Triton
  cache. Model, checkpoint, task, seed, observations, actions, compile setting,
  reward, and success criterion are unchanged.

Status: `PARITY_RETRY_RUNNING` in
`runs/simplewam_libero_plus_parity_v1_retry1`, Slurm step `1593640.276`, after
both allocated A800s were verified at 4 MiB and 0% utilization.
