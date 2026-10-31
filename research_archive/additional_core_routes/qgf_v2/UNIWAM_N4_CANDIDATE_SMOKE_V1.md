# UniWAM Native N4 Candidate Smoke V1

## Admission And Scope

The fixed baseline completed lift_pot/demo_clean scene 1000100000 successfully
in 41 actions, then crashed during process exit after writing its result/video.
Freeze that as CLOSED_LOOP_VALID_EXIT_CRASH, not a clean-exit parity PASS.
Launch this zero-action interface gate only after full video decode and terminal
result audit. No baseline episode is repeated and no QGF outcome is claimed.

## Frozen Inputs And Cost

- Official source commit 8dcd3401bccda8c002fc558e356b975b1789eecd and the exact
  restored RoboTwin policy bundle, checkpoint and assets remain unchanged.
- Same task and engineering scene 1000100000; fixed unseen instruction from
  the completed episode: Hold the kitchenpot with two side handles firmly and lift it.
- Reconstruct the initial scene once. No expert rollout, scene search, dummy
  movement or model action is executed. Capture one observation and reuse it.
- Engineering process initialization seed 202636000; excluded from every
  training, validation and formal set. History-flow, four denoise steps,
  history noise 0.02, future-video fraction 1.0 remain official.
- One assigned idle A800, 8 CPUs, 45 GB RAM. Expected 10-20 minutes, hard
  45 minutes / 0.75 allocated GPU-hours. Preserve failures and their costs.

## Candidate And State Contract

The active inference_step has no seed keyword. All requests call unchanged
official get_action. Candidate0 uses the captured native RNG stream at the
replanning boundary, with no reseeding. Alternatives restore that same policy
memory and set Python, NumPy, Torch CPU/CUDA RNG to 11000, 12000 and 13000.
No decoded action perturbations, clipping, fake rewards or branch labels.

Before the bank, call a direct native reference from the initial snapshot.
Then restore that snapshot for each candidate. After all four requests,
replay candidate0. Also replay the outcome-blind selected index 2 and compare
its action and post-inference policy/RNG state to saved candidate2 state.
Commit means restoring candidate2 post-inference state and returning its exact
chunk, not executing robot actions. Robot transition/commit audits remain a
separate pilot prerequisite.

Snapshots include observation/action caches, current state and normalized state,
first-step flag, previous action, real-qpos history and instruction; Python,
NumPy and Torch CPU/all visible CUDA RNG; VAE temporal caches, registered model
buffers and known positional caches. The official VLM has use_cache=False.
Archive these snapshots and raw input/candidate arrays. Restore the pre-bank
state and verify exact structural hashes before returning.

## Frozen Gate

- Four finite float32 native action chunks with shape [4,16,14]. The official
  adapter uses qpos actions; do not impose another model's binary gripper rule.
- Four distinct SHA256 hashes and minimum pairwise mean absolute difference > 0.
- Candidate0 versus native reference and post-bank replay max error <= 1e-6.
- Selected index 2 replay/returned-chunk error <= 1e-6; selected post-memory/RNG
  exact structural hash equality and pre-bank restoration equality required.
- Zero environment actions; input qpos and cached observation unchanged.
- Save all raw arrays, state/RNG snapshots, per-request latency, measured CUDA
  peak, wall/GPU-hours, source/config/script hashes, and report even on failure.
- A complete valid report is distinct from process-exit status. A teardown
  fault must remain explicit and cannot become a clean exit through marker edits.
- Any scientific audit failure freezes this candidate configuration. Do not
  choose different seeds, task, shapes or tolerances after seeing results.

Only a passed candidate audit admits a separately pre-registered training-only
random-intervention pilot. No critic or online QGF evaluation is admitted here.
