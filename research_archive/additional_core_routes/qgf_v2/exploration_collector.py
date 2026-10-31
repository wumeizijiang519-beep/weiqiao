"""Explicit random-N4 behavior data; never report it as a baseline/QGF result."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unitas_robotwin_candidate_client import CandidatePolicyClient
import unitas_robotwin_gate_client as base
from exploration_contract import choose_random_candidate, validate_commit
import trajectory_collector


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--exploration-log', type=Path, required=True)
    parser.add_argument('--selection-seed', type=int, required=True)
    parser.add_argument('--native-host', required=True)
    parser.add_argument('--native-port', type=int, required=True)
    known, remaining = parser.parse_known_args()
    known.exploration_log.parent.mkdir(parents=True, exist_ok=True)
    if known.exploration_log.exists():
        raise FileExistsError('refusing duplicate exploration log')
    native_type = base.PolicyClient

    class ExplorationClient(CandidatePolicyClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.rng = np.random.default_rng(known.selection_seed)
            self.initial = True

        def reset(self):
            super().reset()
            self.initial = True

        def act(self, observation, instruction, history):
            started = time.monotonic()
            candidates, diversity = self.candidates(observation, instruction, history, 4)
            selected = choose_random_candidate(candidates, self.rng)
            parity_error = None
            if self.initial:
                if history:
                    raise ValueError('initial baseline parity requires empty history')
                with native_type(known.native_host, known.native_port, domain='robotwin') as native:
                    native.reset()
                    reference = np.asarray(native.act(observation, instruction, history), np.float32)
                    validate_commit(candidates, 0, reference)
                    parity_error = float(np.max(np.abs(reference - candidates[0])))
                    native.reset()
                self.initial = False
            committed = self.commit_candidate(observation, instruction, history, selected)
            actions = validate_commit(candidates, selected, committed)
            record = {'behavior': 'uniform_random_WAM_N4_training_only',
                      'selection_seed': known.selection_seed, 'selected_index': selected,
                      'candidate_actions': candidates.tolist(), 'diversity': diversity,
                      'candidate0_native_initial_max_error': parity_error,
                      'commit_max_error': float(np.max(np.abs(actions - candidates[selected]))),
                      'latency_seconds': time.monotonic() - started,
                      'candidate_q': None, 'reward_used_for_selection': False}
            with known.exploration_log.open('a') as stream:
                stream.write(json.dumps(record, allow_nan=False) + '\n')
            return actions

    base.PolicyClient = ExplorationClient
    sys.argv = [sys.argv[0], *remaining]
    trajectory_collector.main()


if __name__ == '__main__':
    main()
