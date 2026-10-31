"""Zero-action V2 contract audit of retained model outputs from two observations."""

import json
from pathlib import Path

import numpy as np

from data_contract_v2 import validate_bank
from wam_runtime import ROOT, file_sha


def main():
    code = ROOT / 'qgf_gradient_v1'
    output = code / 'training288_v2'
    output.mkdir(exist_ok=True)
    destination = output / 'ZERO_ACTION_CONTRACT_GATE.json'
    if destination.exists():
        raise RuntimeError('Never overwrite frozen gate evidence')
    authorization = json.loads((code / 'V2_AUTHORIZATION.json').read_text())
    if authorization['native_gripper_values'] != [-1, 0, 1]:
        raise RuntimeError('Missing explicit V2 authorization')
    diagnostic = ROOT / 'runs/qgf_gradient_native_gripper_diagnostic_v1'
    report = json.loads((diagnostic / 'REPORT.json').read_text())
    if (file_sha(diagnostic / 'REPORT.json') != 'e75bc417c148184c4e73c2caf9207733bd2e4ba1cfa894495f5fbf1b73c9a8ab'
            or not report['context_matches_original'] or report['policy_actions_executed'] != 0):
        raise RuntimeError('Retained diagnostic evidence changed')
    with np.load(diagnostic / 'bank.npz', allow_pickle=False) as data:
        native, raw, scale, offset = [data[key].copy() for key in ['native', 'raw', 'action_scale', 'action_offset']]
    _, failure_bank = validate_bank(native, raw, scale, offset)
    stage0 = ROOT / 'runs/qgf_gradient_zero_action_v1_retry2/arrays.npz'
    with np.load(stage0, allow_pickle=False) as data:
        names = ['w0', 'bank1', 'bank2', 'bank3']
        a = np.stack([data[name] for name in names])
        b = np.stack([data[name + '_normalized'] for name in names])
    _, initial_bank = validate_bank(a, b, scale, offset)
    result = {'status': 'ZERO_ACTION_V2_CONTRACT_PASS', 'new_model_requests': 0,
              'new_environment_actions': 0, 'source': 'Frozen retained actual model-output arrays, not new inference.',
              'failure_observation_contract': failure_bank, 'initial_observation_contract': initial_bank,
              'authorization_sha256': file_sha(code / 'V2_AUTHORIZATION.json'),
              'diagnostic_bank_sha256': file_sha(diagnostic / 'bank.npz'),
              'stage0_arrays_sha256': file_sha(stage0),
              'v2_contract_sha256': file_sha(code / 'data_contract_v2.py'),
              'scope': 'Native/canonical contract only; no efficacy or partial-state reconstruction claim.'}
    destination.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
