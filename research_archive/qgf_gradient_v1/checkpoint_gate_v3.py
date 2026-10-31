"""Two independent checkpoint reconstructions; no new model decision."""

import json
import os
from pathlib import Path
import traceback

from replay_checkpoint_v3 import replay_prefix
from wam_runtime import file_sha


def main():
    run = Path(os.environ['QGF_CHECKPOINT_RUN'])
    run.mkdir(exist_ok=False)
    try:
        *_, history, first = replay_prefix(run / 'first')
        *_, repeated, second = replay_prefix(run / 'second', reference_history=history)
        if history != repeated:
            raise RuntimeError('Controller trace mismatch')
        report = {'status': 'CHECKPOINT_RECOVERY_V3_PASS', 'first': first, 'second': second,
                  'new_policy_decisions': 0, 'new_policy_outcomes': 0,
                  'original_v2_result': 'FAILED; immutable',
                  'protocol_sha256': file_sha(Path(__file__).with_name('CHECKPOINT_RECOVERY_V3.md')),
                  'source_sha256': file_sha(Path(__file__).with_name('replay_checkpoint_v3.py'))}
        (run / 'REPORT.json').write_text(json.dumps(report, indent=2, sort_keys=True))
        (run / 'CHECKPOINT_RECOVERY_V3_PASS').touch()
        print(json.dumps(report, indent=2), flush=True)
    except BaseException:
        (run / 'FAILED.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
