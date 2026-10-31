"""Freeze one interrupted entry only, after a clean V3 checkpoint proof."""

import json
from pathlib import Path

from wam_runtime import ROOT, file_sha


code = ROOT / 'qgf_gradient_v1'
target = code / 'training288_v2/RESUME_ONE_REGISTRATION.json'
if target.exists():
    raise RuntimeError('Never replace a registered attempt')
gate = ROOT / 'runs/qgf_gradient_checkpoint_gate_v3'
if (json.loads((gate / 'REPORT.json').read_text())['status'] != 'CHECKPOINT_RECOVERY_V3_PASS'
        or (gate / 'process_exit_code').read_text().strip() != '0'):
    raise RuntimeError('Checkpoint proof incomplete')
names = ['collect_v2.py', 'data_contract_v2.py', 'data_contract.py', 'core.py', 'wam_runtime.py',
         'replay_checkpoint_v3.py', 'replay_prefix.py', 'collect.py', 'CHECKPOINT_RECOVERY_V3.md',
         'audit_collection_v2.py', 'run_training_shard_v2.sh']
registration = {
    'status': 'REGISTERED_SINGLE_PARTIAL_CONTINUATION', 'episode_ids': ['train_0030'],
    'resume_episode_ids': ['train_0030'], 'manifest_sha256':
    '7194f02c8dba2c9ae01fddab1d0c48c169e28f6778e3926a0386dfeff0307af9',
    'source_sha256': {name: file_sha(code / name) for name in names},
    'checkpoint_gate_sha256': file_sha(gate / 'REPORT.json'),
    'old_failed_gate_not_relabelled': True, 'completed_entries_resampled': 0,
    'prefix_replayed_not_new_data': 210, 'maximum_new_model_steps': 490,
    'hard_wall_seconds': 3000, 'gpu_count': 1,
    'p90_forecast_seconds': 900, 'includes_model_load_and_recovery': True,
    'prior_total_gpu_seconds': 5237 + 92 + 29 + 50,
    'prior_collection_gpu_seconds': 4179 + 92 + 29 + 50,
    'collection_budget_gpu_hours': 24, 'total_budget_gpu_hours': 128,
    'stop_on_any_audit_or_infrastructure_failure': True,
    'next_stage': 'Independent single-episode V2 file/RNG/video audit before other dispatch.'}
target.write_text(json.dumps(registration, indent=2, sort_keys=True))
print(json.dumps({'registration': str(target), 'sha256': file_sha(target)}, indent=2))
