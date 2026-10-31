# Stage0 Authorized Retry Result

Status: ENGINEERING_PASS, clean process exit. Not a learned-Q or online efficacy result.

- Exact Slurm step:1593640.310, COMPLETED, ExitCode0:0,431seconds.
- Run:runs/qgf_gradient_zero_action_v1_retry2.
- User-approved repair only: unique node-local TMPDIR. Frozen model, compile
  settings, seeds, observations, guidance code and tolerances were unchanged.
- Official strict accounting:12,406,309,603parameters, missing0/unexpected0,
  proprio strict. Peak allocated CUDA24,972,581,888bytes.
- Python probe wall316.402seconds; full allocated step431seconds. These are
  different timing scopes and neither is a robot episode latency.
- Native versus zero-guidance maximum error0; native after scheduler restore
  error0; supported-guidance repeat error0. All action arrays finite[32,7].
- Four native candidates have four distinct hashes. Support basis rank3;
  local NumPy recomputation gives orthogonality max error9.536743e-7.
- Actual guidance path is nonzero: native-space maximum output difference
  from official0.0714111626. This is not a success improvement or safety bound.
- Fixed sigma<=0.5 activates only the final one of ten scheduler steps in this
  official schedule. Explicit normalized correction RMS0.0230714511 is below
  the0.05budget. Direct suffix/gripper step corrections are zero.
- The synthetic gradient was deliberately inside the candidate basis, so
  vanilla and projected toy outputs are identical. This test does not show
  superiority of projection; learned-Q and online ablations remain required.
- No actor parameter gradient, no model-source modification, no environment
  instance, no executed robot action, no RL fit. Synthetic linear critics only.

## Budget Including Failures

| Step | State | Allocated GPU seconds |
|---|---|---:|
|1593640.307|FAILED, Hydra before model construction|225|
|1593640.309|FAILED, shared temporary directory during compile|402|
|1593640.310|COMPLETED, engineering audit pass|431|

Total1058seconds=0.293888889GPUh, below the original2GPUh cap. All three
attempts remain recorded. No fourth automatic retry is authorized or needed.

## Frozen Evidence

- report.json SHA256274d1dedfb87723261e2ada53bab88b4becdecb35bad85dd1fad3858f1208a9f
- arrays.npz SHA256024cb78cbc5610a45bd2432317323ae96520ba483f72d36512998a27d6feb3cb
- composed_config.yaml SHA256d7eb9b2f8a3439a17a441155662d520be4c02df13281a0437efda3836910cbb7
- Protocol SHA2567058066bc63b087c5f5018868bbfee7fd7a22436d3ebce53250b657003b9cb06
- User-exception JSON SHA2568d9fff4f523cb24fa68b3d396edf6f9ce2a39981f7491eccac20e4c04080f7bc

Remote SHA manifest verification passed. Local independent NumPy reads of
the downloaded arrays confirmed finiteness, exact replay/restore/w0 equality,
four bank hashes and the nonzero guided output. The full report is mirrored as
STAGE0_REPORT.json; raw evidence as STAGE0_ARRAYS.npz.

Next required work: new cohort collector, action normalization/executed-prefix
and RNG/transition audit, measured cost gate, then real training-only data and
RL critic qualification. The288/64/216scene manifest is frozen, but bulk
collection has not started. No positive QGF performance or submission outcome
is promised.
