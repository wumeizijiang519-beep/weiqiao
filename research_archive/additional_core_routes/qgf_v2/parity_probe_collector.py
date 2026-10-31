"""Capture one feasible observation and diagnose servers; execute ZERO actions."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unitas_robotwin_candidate_client import CandidatePolicyClient
import unitas_robotwin_gate_client as base
import trajectory_collector


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--probe-output', type=Path, required=True)
    parser.add_argument('--fresh-host', required=True)
    parser.add_argument('--legacy-host', required=True)
    known, remaining = parser.parse_known_args()
    native_type = base.PolicyClient
    output = known.probe_output
    if (output / 'parity_probe.json').exists():
        raise FileExistsError('refusing duplicate probe')

    class ProbeClient(CandidatePolicyClient):
        def act(self, observation, instruction, history):
            started = time.monotonic()
            if history:
                raise ValueError('probe must start from initial observation')
            arrays = {}
            health = {}
            arrays['candidates'], diversity = self.candidates(observation, instruction, history, 4)
            arrays['commit0'] = self.commit_candidate(observation, instruction, history, 0)
            self.reset()
            arrays['repeat_candidates'], _ = self.candidates(observation, instruction, history, 4)
            arrays['commit1'] = self.commit_candidate(observation, instruction, history, 1)
            self.reset()
            for name, host, port in (('fresh', known.fresh_host, 18342), ('legacy', known.legacy_host, 18231)):
                with native_type(host, port, domain='robotwin') as native:
                    health[name] = native.session.get(f'http://{host}:{port}/health', timeout=10).json()
                    for repeat in range(2):
                        native.reset()
                        arrays[f'{name}{repeat}'] = np.asarray(native.act(observation, instruction, history), np.float32)
                    native.reset()
            if any(not np.isfinite(value).all() for value in arrays.values()):
                raise ValueError('nonfinite probe outputs')
            comparisons = {}
            pairs = {'candidate_commit0': (arrays['candidates'][0], arrays['commit0']),
                     'candidate_reset_repeat': (arrays['candidates'], arrays['repeat_candidates']),
                     'candidate_commit1': (arrays['repeat_candidates'][1], arrays['commit1']),
                     'fresh_native_repeat': (arrays['fresh0'], arrays['fresh1']),
                     'legacy_native_repeat': (arrays['legacy0'], arrays['legacy1']),
                     'candidate_vs_fresh': (arrays['candidates'][0], arrays['fresh0']),
                     'candidate_vs_legacy': (arrays['candidates'][0], arrays['legacy0']),
                     'fresh_vs_legacy': (arrays['fresh0'], arrays['legacy0'])}
            for name, (left, right) in pairs.items():
                if left.shape != right.shape:
                    raise ValueError('probe output contract mismatch')
                delta = np.abs(left - right)
                comparisons[name] = {'max_abs': float(delta.max()), 'mean_abs': float(delta.mean()),
                                     'strict_1e6_pass': bool((delta <= 1e-6).all())}
            np.savez_compressed(output / 'parity_probe_arrays.npz', **arrays)
            report = {'engineering_only': True, 'executed_policy_actions': 0,
                      'comparisons': comparisons, 'health': health, 'diversity': diversity,
                      'elapsed_seconds': time.monotonic() - started,
                      'note': 'diagnostic completion is NOT parity admission or policy success'}
            (output / 'parity_probe.json').write_text(json.dumps(report, indent=2) + '\n')
            (output / 'PARITY_PROBE_COMPLETE').touch()
            raise SystemExit(0)

    base.PolicyClient = ProbeClient
    sys.argv = [sys.argv[0], *remaining]
    trajectory_collector.main()


if __name__ == '__main__':
    main()
