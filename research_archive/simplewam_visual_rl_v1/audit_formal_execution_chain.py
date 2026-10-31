#!/usr/bin/env python3
import argparse
import ast
import hashlib
import json
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output-name", default="formal_execution_chain_audit_v1")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = {
        "gate": root / "run_formal_wam_compatibility_gate.py",
        "runner": root / "run_online_task_formal_final.py",
        "lane": root / "run_formal_online_lane.sh",
        "finalizer": root / "finalize_formal_online.py",
        "final_audit": root / "audit_formal_online_final.py",
        "gate_wrapper": root / "run_formal_wam_compatibility_gate.sh",
        "dispatcher": root / "dispatch_formal_online_v1.sh",
        "resume_dispatcher": root / "dispatch_formal_resume_4lane_v1.sh",
    }
    errors = []
    for name in ("gate", "runner", "finalizer", "final_audit"):
        try:
            ast.parse(files[name].read_text())
        except Exception as exc:
            errors.append("%s parse: %s" % (name, exc))
    gate = files["gate"].read_text()
    runner = files["runner"].read_text()
    lane = files["lane"].read_text()
    finalizer = files["finalizer"].read_text()
    final_audit = files["final_audit"].read_text()
    gate_wrapper = files["gate_wrapper"].read_text()
    dispatcher = files["dispatcher"].read_text()
    resume_dispatcher = files["resume_dispatcher"].read_text()
    requirements = {
        "gate formal registration": (gate, "formal_online_registration_v1/REGISTRATION.json"),
        "gate special init reshape": (gate, 'states = states.reshape(1, -1)'),
        "gate formal partition": (gate, 'cohort["partitions"]["formal"]'),
        "gate zero action": (gate, '"robot_actions_executed": 0'),
        "gate tolerance": (gate, "restore_error > 1e-6"),
        "runner formal registration": (runner, "formal_online_registration_v1/REGISTRATION.json"),
        "runner special init reshape": (runner, 'states = states.reshape(1, -1)'),
        "runner formal manifest index": (runner, 'task_receipt["formal_manifest_index"]'),
        "runner normalized score bank": (runner, "native_score_bank=native_raw_t"),
        "runner commit receipt": (runner, "commit_max_abs_error"),
        "lane gate requirement": (lane, "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_WAM_COMPATIBILITY_PASS"),
        "lane exact tasks": (lane, 'seq "$LANE" "$LANES" 411'),
        "lane completed skip": (lane, "SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE"),
        "finalizer formal registration": (finalizer, "formal_online_registration_v1/REGISTRATION.json"),
        "finalizer formal execution": (finalizer, "formal_online_execution_v1"),
        "finalizer fixed margin": (finalizer, ">= -0.05"),
        "audit 103 scenes": (final_audit, "set(range(103))"),
        "audit formal execution": (final_audit, "formal_online_execution_v1"),
        "gate explicit job": (gate_wrapper, "FORMAL_WAM_JOB_ID"),
        "gate explicit output override": (gate_wrapper, 'FORMAL_GATE_OUTPUT:-$R/formal_wam_compatibility_v1'),
        "gate explicit available-card authorization": (gate_wrapper, '1581551|1598338'),
        "gate final critic deployment audit": (gate_wrapper, "SIMPLEWAM_VISUAL_QGF_FINAL_CRITIC_DEPLOYMENT_AUDIT_PASS"),
        "dispatcher owned user": (dispatcher, 'squeue -h -j "$JOB" -o %u'),
        "dispatcher WAM name": (dispatcher, "JobName=[^ ]*WAM"),
        "dispatcher final critic deployment audit": (dispatcher, "SIMPLEWAM_VISUAL_QGF_FINAL_CRITIC_DEPLOYMENT_AUDIT_PASS"),
        "dispatcher explicit available-card authorization": (dispatcher, '1581551|1598338'),
        "dispatcher gpu22 single lane": (dispatcher, 'if test "$JOB" = 1598338; then LANES=1; fi'),
        "dispatcher allocated GPU parsing": (dispatcher, "sed -n 's/^TRES=.*gres\\/gpu="),
        "dispatcher exclusive gate": (dispatcher, 'srun --jobid="$JOB" --exclusive'),
        "dispatcher bounded lanes": (dispatcher, 'if test "$LANES" -gt 4'),
        "dispatcher gate before lanes": (dispatcher, "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_WAM_COMPATIBILITY_PASS"),
        "dispatcher requires 412 markers": (dispatcher, 'test "$COMPLETE" -eq 412'),
        "dispatcher requires 412 reports": (dispatcher, 'test "$REPORTS" -eq 412'),
        "dispatcher frozen finalizer": (dispatcher, 'finalize_formal_online.py'),
        "dispatcher independent final audit": (dispatcher, 'audit_formal_online_final.py'),
        "dispatcher final audit marker": (dispatcher, "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_AUDIT_PASS"),
        "dispatcher final hashes": (dispatcher, "FORMAL_ONLINE_FINAL_SHA256SUMS"),
        "resume exact gpu4 job": (resume_dispatcher, "JOB=1581551"),
        "resume independent gpu4 gate": (resume_dispatcher, "formal_wam_compatibility_gpu4_v1"),
        "resume four modulo lanes": (resume_dispatcher, 'bash "$R/run_formal_online_lane.sh" "$LANE" 4'),
        "resume four-CPU allocation": (resume_dispatcher, "--cpus-per-task=4"),
        "resume requires transition receipt": (resume_dispatcher, "GPU22_TO_GPU4_TRANSITION_RECEIPT.txt"),
        "resume requires 412 markers": (resume_dispatcher, 'test "$COMPLETE" -eq 412'),
        "resume requires zero failures": (resume_dispatcher, 'test "$FAILED" -eq 0'),
        "resume frozen finalizer": (resume_dispatcher, "finalize_formal_online.py"),
        "resume independent final audit": (resume_dispatcher, "audit_formal_online_final.py"),
    }
    for label, (text, snippet) in requirements.items():
        if snippet not in text:
            errors.append("missing " + label)
    registration_path = root / "formal_online_registration_v1" / "REGISTRATION.json"
    registration = json.loads(registration_path.read_text())
    if len(registration.get("tasks", [])) != 412 or len(registration.get("scenes", [])) != 103:
        errors.append("registration cardinality")
    if registration.get("outcomes_read_during_registration") != 0:
        errors.append("registration outcomes")
    status = "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_EXECUTION_CHAIN_AUDIT_PASS" if not errors else "SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_EXECUTION_CHAIN_AUDIT_FAIL"
    output_dir = root / args.output_name
    output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "status": status,
        "errors": errors,
        "sources": {name: {"path": str(path), "sha256": sha256(path)} for name, path in files.items()},
        "registration_sha256": sha256(registration_path),
        "robot_actions_executed": 0,
        "formal_outcomes_read": 0,
        "scenes": 103,
        "tasks": 412,
    }
    report_path = output_dir / "REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (output_dir / status).write_text("\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
