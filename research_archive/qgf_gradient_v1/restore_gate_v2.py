"""Two independent physics reconstructions, no new policy/model inference."""

import json
import os
from pathlib import Path
import traceback

from replay_prefix import replay_prefix
from wam_runtime import ROOT, file_sha


def main():
    run = Path(os.environ['QGF_RESTORE_RUN'])
    if run.exists():
        raise RuntimeError('Never overwrite a restoration gate run')
    run.mkdir()
    code = ROOT / 'qgf_gradient_v1'
    gate = code / 'training288_v2/ZERO_ACTION_CONTRACT_GATE.json'
    if json.loads(gate.read_text())['status'] != 'ZERO_ACTION_V2_CONTRACT_PASS':
        raise RuntimeError('Zero-action V2 contract gate not passed')
    try:
        *_, history, first = replay_prefix(run / 'first')
        *_, repeated_history, second = replay_prefix(run / 'second', reference_history=history)
        if history != repeated_history:
            raise RuntimeError('Full controller histories differ')
        report = {'status': 'RESTORE_GATE_PASS', 'first': first, 'second': second,
                  'zero_action_contract_sha256': file_sha(gate),
                  'authorization_sha256': file_sha(code / 'V2_AUTHORIZATION.json'),
                  'new_policy_decisions': 0, 'new_policy_outcomes': 0,
                  'archival_physics_replay_actions': 2 * (210 + 30),
                  'replay_source_sha256': file_sha(code / 'replay_prefix.py')}
        (run / 'REPORT.json').write_text(json.dumps(report, indent=2, sort_keys=True))
        (run / 'RESTORE_GATE_PASS').touch()
        print(json.dumps(report, indent=2), flush=True)
    except BaseException:
        (run / 'FAILED.txt').write_text(traceback.format_exc())
        print((run / 'FAILED.txt').read_text(), flush=True)
        raise


if __name__ == '__main__':
    main()
