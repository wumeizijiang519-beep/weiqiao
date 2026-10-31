# Status

- A prospective full-data final-critic retraining branch is active to correct
  the identified reference-pipeline gap without altering the frozen Online V2
  result. Simple-WAM, exported features, RL token, corpus, rewards, action
  coordinates, K=10, QGF settings, and all prior evidence remain immutable.
- Three fixed seeds now train on all 12,218 training transitions for 50,000
  updates at batch 64. Source/registration audit status is
  `SIMPLEWAM_VISUAL_IQL_FINAL_SOURCE_AUDIT_PASS`; protocol SHA is
  `1b8ede9a7c0d987d31a1585892f525928fac844653a83566e244ea194c84765f`
  and trainer SHA is
  `10feac33be94c182b00290e0113951ba99cf762157af2a9b6a459f27da2feaf6`.
- Active training steps are 1598338.64 (seed 202644201), 1598338.65
  (seed 202644202), and 1673999.8 (seed 202644203), using three critic-only
  A800s. Two early orchestration cancellations are retained as infrastructure
  partials; they changed no scientific byte and their seed runs restarted from
  step zero in new immutable directories.
- Existing validation outcomes are consumed and forbidden for checkpoint
  selection. A new online claim requires previously untouched formal/test
  scenes registered before outcomes are read.
- Online V2 is complete: 240/240 tasks, 60 held-out scenes x four arms, with
  zero failed task receipts. The frozen finalizer status is
  `NO_SIMPLEWAM_VISUAL_QGF_ONLINE_BENEFIT`; independent recomputation passed as
  `SIMPLEWAM_VISUAL_QGF_ONLINE_V2_FINAL_AUDIT_PASS` with no errors.
- Official success was candidate0 44/60 (73.3%), uniform random 44/60 (73.3%),
  critic rerank 35/60 (58.3%), and visual QGF 43/60 (71.7%). Visual QGF minus
  candidate0 was -1.7 points (bootstrap 95% [-11.7, 8.3]); versus random it
  was -1.7 points ([-8.3, 5.0]); versus rerank it was +13.3 points
  ([3.3, 23.3]). Thus QGF recovered the critic-rerank degradation but did not
  beat candidate0 or random under the preregistered endpoint.
- Final REPORT SHA is
  `0a46b4394ace3c6420018bbff58a83a1ccf39a908f94bcaa02151eb59215cc82`;
  independent audit REPORT SHA is
  `e4c0b8fcacbd12ebfd43bab41b72bfd43ba8614393639b2db70a043123480483`.
  Job 1677369 was released after evidence freezing. No online benefit is
  claimed and this exact configuration must not be rerun or retuned.
- Acceleration audit passed for an orchestration-only eight-lane layout, but a
  bounded live trial showed that two Simple-WAM processes per GPU exceed the
  job's 256 GB host-memory envelope (about 34 GB RSS per process). The trial
  produced no completed tasks; all partial task directories, logs, Slurm cost,
  and hashes are retained as infrastructure evidence.
- Online V2 resumed without changing any scientific byte as four stable lanes,
  one process per A800, steps 1677369.20 through 1677369.23. The first 56 tasks
  remain immutable and are skipped; execution restarts at tasks 056 through
  059, with zero failed task receipts at cutover.
- Online V1 stopped after 13 complete tasks when task 006 triggered the frozen
  critic-support fail-closed check. Its all-64-scene analysis is unavailable;
  partial artifacts and costs are frozen, and no online benefit is claimed.
- A prospective V2 uses only untouched validation scenes 4..63. Baseline arms
  no longer require critic support; Q-based arms use supported candidates and
  abstain to candidate0 only when none are supported. Models, support bounds,
  seeds, compute, and statistical thresholds are unchanged.
- V2 registration covers 60 scenes/240 tasks, registration SHA
  `2c248d11bbf56166c4f5d2c13b049ce8d5871d2a9839b431ae871880a750a4fe`.
  Registration and execution-source audits passed with zero actions.
- Job 1677369 is now running on four gpu21 A800s. Its first zero-action gate
  failed because the node image omitted NVIDIA EGL graphics libraries; no
  online outcome or robot action was produced.
- A bounded infrastructure repair staged the exact 64-bit NVIDIA EGL libraries
  from a node with the identical 535.104.05 driver, froze their hashes, and
  verified `MUJOCO_EGL_IMPORT_PASS`. The gate and lane wrappers only add this
  library path and vendor manifest; the retry3 source audit passed.
- The single-task compatibility gate is now running as step 1677369.7 and has
  reached construction of the unchanged frozen WAM. Online lanes remain gated
  until EGL, layer-29 features, replay, and the 1e-6 checks all pass.
- Mainline reset from fallback projection experiments to the original visual-RL
  chain: Simple-WAM visual token -> TwinQ/IQL -> shared rerank/QGF critic.
- The frozen backbone is Simple-WAM on LIBERO; Tau0 is no longer a runtime
  dependency.
- The immutable layer-29, stride-4, two-camera feature export covers all 288
  training episodes and 12,506 observations; the independent audit passed.
- The outcome-blind RL token completed 10,000 updates and passed independent
  audit with 11,242 training and 1,264 validation observations.
- The critic corpus contains 12,218 source-verified transitions from 137
  physical groups. Actual execution length is used only in the TD target, never
  in the current Q input.
- All nine fixed seed/fold TwinQ/IQL workers completed. Every seed beat the
  state-only and within-group action-permutation controls under group-equal
  bootstrap, and the independent qualification audit passed.
- The outcome-independent nine-checkpoint conservative ensemble is frozen for
  both candidate reranking and QGF. The zero-action deployment audit confirms
  finite rerank scores and action gradients, with exactly zero suffix/gripper
  modification and no gradients on token or critic parameters.
- The held-out online comparison is frozen before reading outcomes: 64
  validation scenes, four deterministic result-independent arm orders, and 256
  scene-arm tasks. Every arm computes the same native bank, critic scores, and
  shadow Q-gradient work; only the committed action differs.
- The live executor, equal-compute scheduler, compatibility gate, and four
  disjoint GPU lanes passed source and mock-contract audits. The watcher will
  launch all four lanes automatically if and only if the active gate passes.
- The original WAM allocation expired; job 1677369 is its active four-GPU
  replacement.
- No online QGF benefit is claimed.
- 2026-10-30 final-critic heartbeat: all three full-data final critics completed
  the fixed 50,000 updates on all 12,218 training transitions. Independent
  status is `SIMPLEWAM_VISUAL_IQL_FINAL_AUDIT_PASS` (REPORT SHA
  `0e53d0ab2432c33924010bd82ec28b852c6e0a1b286ff262f57d415c36f558ab`).
  Checkpoint SHAs are `6ef96cfa43396a06b583952ba28a2b7b684fb3958f490a3fc83cab780c981dab`,
  `4d22e6a01e0ccc69b278de1caecada99b9a5461b0ddf72bdf1da6e014ea05fcf`,
  and `1e5faeb55a8af41aa9aa049548ba76f6d7f16c7b6528305f2d34403758e16e55`.
  Their action sensitivities are 0.05877, 0.05329, and 0.05207. The fixed
  deployment ensemble is the arithmetic mean of all three `min(Q1,Q2)` values;
  no validation or online outcome selected a seed or checkpoint. Ensemble
  registration SHA is
  `609a274798f4ba9686e6ee460ffa6c0f717784d8caa27f8dd7829c78d81c9bc7`.
- Read-only inventory found an untouched formal partition with 216 manifest
  entries and 103 unique physical groups. Formal groups have zero overlap with
  the 137 training and 42 consumed validation groups, and every referenced
  BDDL/init asset matches its frozen hash. One result-independent SHA-ranked
  entry per physical group is now prospectively registered as 103 scenes x
  four arms = 412 tasks. Registration SHA is
  `4c5b6865817f91480c7618b2f9833fc1437dfb2623ce267769345153489de196`;
  independent registration and zero-action source audits both pass. No formal
  outcome has been read and no formal robot action has executed.
- There is currently no explicitly allocated WAM-compatible job in Slurm.
  gpu22/gpu4 remain critic-only and must not be forced to run WAM. The next
  heartbeat must monitor for a new owned WAM allocation; once available, run a
  zero-action EGL/layer29/replay/1e-6/final-ensemble gate before launching
  disjoint multi-GPU formal lanes. The consumed validation64 remains historical
  only and must never be reused as prospective evidence.
- 2026-10-30 12:38 CST heartbeat: formal execution readiness is now complete.
  `run_formal_wam_compatibility_gate.py`, the four-way resumable lane wrapper,
  the 103-scene finalizer, and its independent audit are frozen. Execution-chain
  audit status is
  `SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_EXECUTION_CHAIN_AUDIT_PASS`, REPORT SHA
  `798098e82d2936a948354c7e5e21d06b08cd0d34b9939ed5f0c952ea8ca47370`.
  A synthetic 412-task receipt set exercised finalization and independent
  recomputation end to end and passed; it is mock-only and is not scientific
  evidence. Formal outcomes read and formal robot actions remain zero.
- Slurm still exposes no owned WAM-compatible allocation. Existing gpu22/gpu4
  allocations remain critic-only. This is now the only blocker to the frozen
  prospective formal run and is a platform-deadline risk.
- 2026-10-30 13:08 CST: fail-closed formal orchestration is frozen. The new
  dispatcher accepts only an explicitly supplied, owned, RUNNING WAM job newer
  than consumed job 1677369; it launches one exclusive zero-action gate and at
  most four one-process-per-GPU lanes only after gate PASS. Execution-chain V2
  audit PASS, REPORT SHA
  `f8f413079a32a63143cd0f89b1d11585dcdb2facdafdcf169183fe6e99a1acdd`.
  Existing job 1581551 was deliberately tested and rejected before directory
  creation with exit 1; formal outcomes/actions remain zero. No eligible new
  WAM allocation is present.
- 2026-10-30 13:38 CST: formal dispatcher now closes the full evidence loop.
  After all bounded lanes return, it requires exactly 412 complete markers and
  412 task reports before running the frozen finalizer and independent audit;
  it then freezes both report SHAs. V3 chain audit PASS, REPORT SHA
  `14165602e336ea722c29fb440827267a29f2c815542e71e512d23d6711f9ff98`;
  dispatcher SHA
  `e740488272906c0d11b977f688ac90961fb1fa45ce2c35e9c89842120cba2df2`.
  Existing job 1581551 remains rejected with exit 1 and zero actions. No new
  compatible WAM allocation exists.
- 2026-10-30 14:08 CST: the three-seed full-data final ensemble passed a real
  critic-only GPU deployment audit on gpu22 step 1598338.66 (COMPLETED 0:0,
  20s). N4 rerank scores were finite and nontrivial, selected index 1, raw Q
  gradient norm was 0.0236631, and suffix/gripper errors were exactly zero.
  WAM parameters loaded=0, robot actions=0, formal outcomes read=0. Deployment
  audit REPORT SHA is
  `e35efe50602efbb446604df382562e8ca0cb80cb1b296dc990add10f8e60822b`;
  independent audit PASS REPORT SHA is
  `5307cdd6c8081270d2041211459cbee2018db4194348f969a3f07ee419096b37`.
  The formal gate and dispatcher now require this PASS marker. Updated chain V4
  audit PASS REPORT SHA is
  `0c466e41d7e65407547f56b21a709111cf0e11ad59cd4859d54b516c695c3a4a`.
  No WAM-compatible allocation is currently available.
- 2026-10-30 14:38 CST: a runtime-only budget audit used the 240 consumed
  validation task wall-times without reading any success/outcome field. Mean
  task time is 244.16s and P90 is 340.67s. The frozen 412-task formal run on
  four lanes projects to 6.99h mean makespan / 27.94 GPUh; the conservative
  P90-task projection is 9.75h. With a fixed 1h gate/safety margin, the latest
  safe four-GPU start is 2026-10-31 13:15 CST for the 2026-10-31 24:00 CST
  platform deadline. Runtime-budget audit PASS, REPORT SHA
  `a2f25bf11f7f6328e68e67fb265204c87b6b98f2abed1b971e214705b25dca31`.
  No compatible WAM allocation exists, so obtaining a new four-GPU WAM job is
  now the only external action and a time-critical requirement.
- 2026-10-30 15:13 CST: recovery backup now includes all three final critic
  checkpoints and the 849 MiB frozen RL-token checkpoint under
  `D:/qgf_evidence/simplewam_visual_rl_v1/final_critic_formal_20261030/checkpoints`.
  All four local SHA256 values exactly match the remote frozen registrations.
  No WAM allocation appeared and formal execution remains unstarted.
- 2026-10-30 16:25 CST: at the user's explicit request to use available owned
  cards before platform retirement, exact owned allocation job 1581551
  (`OpenWAM_5_0`, four A800 GPUs) was authorized by the orchestration-only
  `FORMAL_AVAILABLE_CARD_AMENDMENT.md`. Formal execution-chain audit V6 PASS
  REPORT SHA is
  `c75261675274613e28b8bbcdc929b3fec7e9456804c4065572a5eff2f7e6593b`;
  it confirms 103 scenes / 412 tasks, zero formal outcomes read, and zero
  robot actions. The first dispatcher invocation stopped before the gate
  because this legacy allocation reports GPU count under `TRES=` rather than
  `AllocTRES=`; its log/PID are archived. The bounded parser repair changed no
  scientific byte. The effective dispatcher is PID 11562 and the sole strict
  zero-action compatibility gate is Slurm step 1581551.376. Gate PASS remains
  mandatory before the dispatcher can launch four exclusive one-GPU formal
  lanes; do not duplicate the dispatcher or gate.
- 2026-10-30 16:34 CST: strict gate attempts on gpu4 and gpu22 both stopped
  before runtime/actions at the initial-state SHA check. Source comparison
  proved an infrastructure bug: the first registered formal asset is
  `_add_17.pruned_init`; the frozen online runner reshapes `_add_`/`_level`
  arrays to one row before indexing, while the gate omitted that branch. Both
  failures and costs are archived, with zero robot actions/outcomes and no
  formal lane. The gate was minimally aligned to the already audited runner;
  execution-chain audit V8 PASS REPORT SHA is
  `dd0f3ef92228bd1e056a13a77d743a83453991cef579762f87b031e1ffee951b`.
  The sole bounded retry is active on idle gpu22 as step 1598338.69 under
  dispatcher PID 44631. It has passed the corrected initial-state check and
  checkpoint accounting and is constructing/compiling the unchanged WAM.
  No task has executed yet; do not duplicate this gate or dispatcher.
- 2026-10-30 16:42 CST: corrected strict gate step 1598338.69 PASS with
  robot_actions_executed=0, initial-state restore max error 1.21e-08,
  bitwise-repeat feature error 0, native/raw replay errors 0, and 10 shadow /
  10 guided denoising steps. Exit code is 0. Dispatcher PID 44631 has started
  the sole memory-bounded formal lane as step 1598338.70 (launcher PID 31437)
  on gpu22. No formal task was complete at launch. Do not launch any duplicate
  lane or second WAM process; continue from the existing task receipts only.
- 2026-10-30 17:43 CST: the healthy single gpu22 lane completed tasks 0..7
  with zero FAILED receipts, but observed throughput near eight tasks/hour
  risks missing the platform deadline. Since the prior gpu4 failure is now
  proven to be the corrected loader bug rather than a GPU result, execution
  chain V9 audit PASS authorized a separate zero-action gpu4 compatibility
  receipt. Exact gate step 1581551.377 (launcher PID 25576) is now active on
  owned OpenWAM job1581551 while gpu22 continues task8. No extra formal lane
  may start until this independent gate passes and the active task boundary is
  coordinated without duplicates.
