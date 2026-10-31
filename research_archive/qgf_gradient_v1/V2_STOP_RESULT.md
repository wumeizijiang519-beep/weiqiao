# V2 Continuation Stopped at the Approved Restoration Gate

Date: 2026-10-26, Asia/Shanghai. The user approved the V2 native gripper
correction conditionally: exact restoration must pass before collection can
continue, and restoration failure must stop this version.

The V2 native gripper contract passed CPU tests and a zero-action check against
frozen real model outputs from two retained observations. Native/raw/canonical
mapping errors were zero, including the official neutral gripper value 0. This
audit generated no new model request or robot-policy decision.

The registered reconstruction step 1593640.319 failed 1:0 after 67 seconds.
It replayed 30 archived dummy actions and 60 archived model actions before the
first observation mismatch at boundary 6. No prior simulator-state mismatch was
reported. The main camera differed in 24 of its 196,608 uint8 color elements,
maximum absolute difference 121, mean absolute difference 0.0112660726. Wrist
camera, end-effector position/quaternion and gripper position were identical.
The full 210-step controller/RNG reconstruction and the second replay did not
complete. Those facts do not satisfy the approved strict observation gate.

Accordingly, no tolerance was changed and no continuation, replacement episode,
new dataset or critic fit was launched. Four integrity entries and 26 completed
shard entries remain preserved under their original audits. The partial
train_0030 retains its 210 real steps and has no final outcome; it is not counted
as a policy failure. The remaining 257 entries are untouched.

Collection GPU cost including the failed attempt and both diagnostics is
4,179 seconds = 1.160833333 GPU hours. Stage0 separately cost 1,058 seconds;
the combined scientific-attempt total is 1.454722222 GPU hours. No budget reset.
The parent allocation and unrelated actors were not terminated.

The 45-minute qgf-wam-rl automation was deleted through the app after this
authorized stop condition. Audio remains disabled; no sound, unmute or volume
change occurred in this heartbeat. New sampling or a changed recovery criterion
requires a new explicit scientific decision. No further backbone rotation or
automatic gate revision is authorized.

This is an engineering recovery failure before RL qualification or online QGF
evaluation, not a finding that QGF is ineffective. It does not complete the
planned paper experiment and cannot support a positive performance claim.

Frozen machine result: training288_v2/STOP_RESULT.json,
SHA256 ba9bd2cdbe03910d8ab6d0327f3d431dcac64fec5e136ccaab2612e7ba8f66c4.
Mismatch arrays remain in
runs/qgf_gradient_v2_restore_gate_v1/first/first_observation_mismatch.npz.
The original V1 data, failure, proposal, approval and source snapshots remain.
