"""Freeze the authorized restoration stop without new simulation or fitting."""

import json

import numpy as np

from wam_runtime import ROOT, file_sha


def main():
    code = ROOT / 'qgf_gradient_v1'
    run = ROOT / 'runs/qgf_gradient_v2_restore_gate_v1'
    destination = code / 'training288_v2/STOP_RESULT.json'
    if destination.exists():
        raise RuntimeError('Never overwrite a stop result')
    failure = (run / 'FAILED.txt').read_text()
    if 'Exact archived observation mismatch at boundary6' not in failure:
        raise RuntimeError('Unexpected failure; do not invent an explanation')
    if (run / 'process_exit_code').read_text().strip() != '1' or (run / 'RESTORE_GATE_PASS').exists():
        raise RuntimeError('Process/gate evidence disagrees')
    mismatch = run / 'first/first_observation_mismatch.npz'
    differences = {}
    with np.load(mismatch, allow_pickle=False) as data:
        for key in [name[7:] for name in data.files if name.startswith('actual_')]:
            actual, expected = data['actual_' + key], data['expected_' + key]
            delta = np.abs(actual.astype(np.float64) - expected.astype(np.float64))
            differences[key] = {'shape': list(actual.shape), 'dtype': str(actual.dtype),
                                'different_elements': int(np.count_nonzero(actual != expected)),
                                'max_abs_error': float(delta.max()), 'mean_abs_error': float(delta.mean())}
    preservation = code / 'gripper_failure_v1/PRESERVATION_AUDIT.json'
    kept = json.loads(preservation.read_text())
    integrity = ROOT / 'runs/qgf_gradient_collector_integrity_v1/INDEPENDENT_AUDIT.json'
    initial = json.loads(integrity.read_text())
    ids = [row['episode_id'] for row in initial['episodes'] + kept['complete_episode_audits']]
    if len(ids) != 30 or len(set(ids)) != 30:
        raise RuntimeError('Complete preserved entries are not uniquely30')
    result = {
        'status': 'STOPPED_APPROVED_RESTORATION_GATE_FAILED',
        'v2_gripper_contract_gate': 'PASS_ON_RETAINED_REAL_MODEL_OUTPUTS',
        'restoration_gate': 'FAIL_EXACT_BOUNDARY_OBSERVATION',
        'first_failed_boundary': 6, 'archived_model_steps_replayed_before_stop': 60,
        'dummy_wait_steps_replayed': 30, 'new_policy_decisions': 0,
        'simulation_state_mismatch_reported_before_observation_failure':
            (run / 'first/first_state_mismatch.npz').exists(),
        'second_reconstruction_started': (run / 'second').exists(),
        'full210step_controller_rng_reconstruction_complete': False,
        'observation_differences': differences,
        'mismatch_npz_sha256': file_sha(mismatch), 'failure_trace_sha256': file_sha(run / 'FAILED.txt'),
        'restoration_step': {'step': '1593640.319', 'state': 'FAILED', 'exit_code': '1:0',
                             'elapsed_seconds': 67, 'allocated_gpu_count': 1},
        'collection_gpu_costs_seconds': {'integrity1593640.314': 819, 'failed1593640.316': 2825,
                                        'diagnostic1593640.317': 468, 'restore1593640.319': 67},
        'collection_gpu_hours': 4179 / 3600, 'stage0_gpu_seconds': 1058,
        'all_scientific_attempt_gpu_hours': 5237 / 3600,
        'preserved_complete_episode_ids': sorted(ids), 'preserved_complete_count': 30,
        'partial_episode': 'train_0030', 'partial_archived_real_steps': 210,
        'partial_episode_outcome': None, 'untouched_training_entries': 257,
        'preservation_audit_sha256': file_sha(preservation),
        'authorization_sha256': file_sha(code / 'V2_AUTHORIZATION.json'),
        'zero_action_contract_sha256': file_sha(code / 'training288_v2/ZERO_ACTION_CONTRACT_GATE.json'),
        'threshold_or_population_change': False, 'continuation_launched': False,
        'real_data_critic_fits': 0, 'new_online_comparisons': 0,
        'scope': 'Engineering recovery stop under the user-approved condition; not evidence of QGF efficacy/failure.',
        'audio_alerts': 'DISABLED_BY_USER',
        'next_action': 'Freeze and stop this authorized continuation. No automatic tolerance change, replacement scene, fresh episode rerun or new backbone.'
    }
    destination.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
