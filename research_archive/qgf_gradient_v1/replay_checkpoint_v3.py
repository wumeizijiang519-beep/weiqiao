"""Restore physical history plus the archived sensor snapshot, without new decisions.

Raster reconstruction is diagnosed, never relabelled as bitwise reproducible.
The resumed policy receives the original measured observation at this boundary.
"""

import copy
import json
import hashlib
from pathlib import Path

import numpy as np
import torch

from collect import seed_environment
from data_contract import (array_hash, capture_rng, load_rng, observation_hash,
                           observation_payload, restore_rng, rng_hash)
from wam_runtime import ROOT, file_sha


PARTIAL = ROOT / 'runs/qgf_gradient_training288_v1_shard0/train_0030'


def controller_signature(env):
    skipped = {'sim', '_sim', 'model', '_model', 'mj_model', 'mj_data'}

    def capture(value, depth=0):
        if isinstance(value, np.ndarray):
            if value.dtype.hasobject:
                return {'unsupported_array_dtype': str(value.dtype)}
            return {'array': array_hash(value), 'shape': list(value.shape), 'dtype': str(value.dtype)}
        if isinstance(value, np.generic):
            return capture(value.item(), depth)
        if isinstance(value, float) and not np.isfinite(value):
            return {'nonfinite_scalar': str(value)}
        if value is None or isinstance(value, (str, bool, int, float)):
            return value
        if isinstance(value, dict):
            return {str(key): capture(item, depth + 1) for key, item in sorted(value.items())}
        if isinstance(value, (list, tuple)):
            return [capture(item, depth + 1) for item in value]
        if depth < 4 and hasattr(value, '__dict__'):
            return {key: capture(item, depth + 1) for key, item in sorted(vars(value).items())
                    if key not in skipped and not callable(item)}
        return {'unsupported_type': type(value).__module__ + '.' + type(value).__qualname__}

    states = []
    for robot in env.robots:
        states.append({'controller': capture(robot.controller),
                       'gripper_current_action': capture(robot.gripper.current_action)})
    encoded = json.dumps(states, sort_keys=True, allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest(), states


def replay_prefix(output, reference_history=None, keep_environment=False, frame_callback=None):
    from experiments.libero.libero_utils import LIBERO_ENV_RESOLUTION, get_libero_dummy_action, get_libero_env
    from libero.libero import benchmark

    output.mkdir(exist_ok=False)
    entry = json.loads((PARTIAL / 'config.json').read_text())
    for path_key, sha_key in [('initial_state_path', 'initial_file_sha256'), ('bddl_path', 'bddl_sha256')]:
        if file_sha(entry[path_key]) != entry[sha_key]:
            raise RuntimeError('Frozen prefix scene asset changed')
    states = np.asarray(torch.load(entry['initial_state_path'], map_location='cpu', weights_only=False))
    initial = np.asarray(states[entry['initial_state_index']], dtype='<f8')
    suite = benchmark.get_benchmark_dict()['libero_10']()
    task = suite.get_task(entry['task_id'])
    if task.name != entry['task_name']:
        raise RuntimeError('Task catalogue changed')
    seed_environment(entry['environment_seed'])
    env, description = get_libero_env(task, LIBERO_ENV_RESOLUTION, entry['environment_seed'])
    closed, passed = False, False
    history, state_checks, boundary_checks = [], 0, 0
    raster_audit = {}
    try:
        env.reset()
        obs = env.set_init_state(initial)
        init = np.load(PARTIAL / 'initialization.npz', allow_pickle=False)

        def check_state(expected, label):
            nonlocal state_checks
            actual = np.asarray(env.get_sim_state()).copy()
            if not np.array_equal(actual, expected):
                np.savez_compressed(output / 'first_state_mismatch.npz', expected=expected, actual=actual,
                                    label=np.asarray(label))
                raise RuntimeError('Exact archived simulator-state mismatch at ' + label)
            state_checks += 1
            signature, raw = controller_signature(env)
            position = len(history)
            if reference_history is not None and signature != reference_history[position]['signature']:
                (output / 'first_controller_mismatch.json').write_text(json.dumps(
                    {'label': label, 'expected': reference_history[position], 'actual': raw}, indent=2))
                raise RuntimeError('Controller-history repeat mismatch at ' + label)
            history.append({'label': label, 'signature': signature})

        def check_observation(index):
            nonlocal boundary_checks
            with np.load(PARTIAL / f'observation_{index:04d}.npz', allow_pickle=False) as saved:
                expected = {key: saved[key] for key in saved.files}
                actual = observation_payload(obs)
                fields = {}
                for key in actual:
                    delta = np.abs(actual[key].astype(np.float64) - expected[key].astype(np.float64))
                    fields[key] = {'equal': bool(np.array_equal(actual[key], expected[key])),
                                   'changed_values': int(np.count_nonzero(delta)),
                                   'max_abs': float(delta.max())}
                    if actual[key].ndim != 3 and not fields[key]['equal']:
                        raise RuntimeError('Non-image sensor differs at boundary ' + str(index))
                raster_audit[str(index)] = fields
                if observation_hash(actual) != observation_hash(expected):
                    target = output / f'render_difference_{index:04d}.npz'
                    if not target.exists():
                        np.savez_compressed(target,
                                            **{'actual_' + key: value for key, value in actual.items()},
                                            **{'expected_' + key: value for key, value in expected.items()})
            boundary_checks += 1

        check_state(init['actual_initialized'], 'initialized')
        init.close()
        if frame_callback is not None:
            frame_callback(obs)
        with np.load(PARTIAL / 'dummy_wait.npz', allow_pickle=False) as dummy:
            for index in range(30):
                obs, reward, _, _ = env.step(get_libero_dummy_action())
                if float(reward) != float(dummy['rewards'][index]):
                    raise RuntimeError('Dummy wait reward mismatch')
                check_state(dummy['sim_states'][index + 1], 'wait_' + str(index))
                if frame_callback is not None:
                    frame_callback(obs)
                env.check_success()
        check_observation(0)
        expected_episode_rng = load_rng(PARTIAL / 'episode_rng.npz')
        if rng_hash(capture_rng()) != rng_hash(expected_episode_rng):
            raise RuntimeError('Caller RNG differs after deterministic dummy waits')
        selection = np.random.default_rng(entry['selection_seed'])
        logical_steps = 0
        paths = sorted(PARTIAL.glob('transition_*/transition.npz'))
        if len(paths) != 21:
            raise RuntimeError('Unexpected archived prefix length')
        for boundary, path in enumerate(paths):
            with np.load(path, allow_pickle=False) as loaded:
                data = {key: loaded[key].copy() for key in loaded.files}
            if path.parent.name != f'transition_{boundary:04d}':
                raise RuntimeError('Noncontiguous archived prefix')
            check_observation(boundary)
            before = load_rng(path.parent / 'rng_before.npz')
            if rng_hash(capture_rng()) != rng_hash(before):
                raise RuntimeError('Archived pre-inference caller RNG mismatch')
            selected = int(selection.integers(0, 4))
            if selected != int(data['selected_index']):
                raise RuntimeError('Archived selection RNG mismatch')
            # Native model inference is deliberately not repeated while reconstructing physics.
            restore_rng(load_rng(path.parent / 'rng_caller_committed.npz'))
            for step, action in enumerate(data['executed_actions']):
                obs, reward, done, _ = env.step(action.copy())
                success = bool(env.check_success())
                if (float(reward) != float(data['rewards'][step])
                        or bool(done) != bool(data['step_environment_done'][step])
                        or success != bool(data['step_success'][step])):
                    raise RuntimeError('Actual feedback differs during archived replay')
                check_state(data['sim_states'][step + 1], f'boundary_{boundary}_step_{step}')
                logical_steps += 1
                if frame_callback is not None:
                    frame_callback(obs)
            check_observation(boundary + 1)
            if rng_hash(capture_rng()) != rng_hash(load_rng(path.parent / 'rng_after_execution.npz')):
                raise RuntimeError('Caller RNG differs after archived execution')
        if logical_steps != 210:
            raise RuntimeError('Wrong reconstructed logical step count')
        failed_boundary = PARTIAL / 'transition_0021'
        if rng_hash(capture_rng()) != rng_hash(load_rng(failed_boundary / 'rng_before.npz')):
            raise RuntimeError('Failed-boundary caller RNG differs after reconstruction')
        selected_record = json.loads((failed_boundary / 'selection.json').read_text())
        if selection.bit_generator.state != selected_record['before']:
            raise RuntimeError('Selection state differs at failed boundary')
        preview = copy.deepcopy(selection)
        if int(preview.integers(0, 4)) != selected_record['selected_index']:
            raise RuntimeError('Failed-boundary selection preview differs')
        if reference_history is not None and len(reference_history) != len(history):
            raise RuntimeError('Controller-history trace length differs')
        # The sensor sample is part of the checkpoint, not regenerated evidence.
        # No environment action, reward, model output or simulator state is changed.
        with np.load(PARTIAL / 'observation_0021.npz', allow_pickle=False) as saved:
            retained = {key: saved[key].copy() for key in saved.files}
        obs = dict(obs)
        obs.update(retained)
        if observation_hash(observation_payload(obs)) != observation_hash(retained):
            raise RuntimeError('Retained sensor snapshot restoration failed')
        np.savez_compressed(output / 'restored_sensor_snapshot.npz', **observation_payload(obs))
        (output / 'raster_reconstruction_audit.json').write_text(json.dumps(raster_audit, indent=2))
        (output / 'controller_history.json').write_text(json.dumps(history, indent=2))
        report = {'status': 'PHYSICAL_HISTORY_AND_RETAINED_SENSOR_CHECKPOINT_RESTORED', 'logical_prefix_steps': logical_steps,
                  'archived_model_actions_replayed': logical_steps, 'dummy_actions_replayed': 30,
                  'new_policy_decisions': 0, 'simulator_state_exact_checks': state_checks,
                  'boundary_observation_diagnostic_checks': boundary_checks,
                  'non_image_sensors_exact': True,
                  'raw_raster_reconstruction_bitwise_exact': all(
                      all(value['equal'] for value in fields.values()) for fields in raster_audit.values()),
                  'resume_policy_input': 'Original measured observation_0021.npz, restored exactly; not a new render.',
                  'resume_observation_sha256': file_sha(PARTIAL / 'observation_0021.npz'),
                  'controller_history_matches_reference': reference_history is not None,
                  'caller_rng_at_resume': rng_hash(capture_rng()),
                  'selection_state_at_resume': selection.bit_generator.state,
                  'limits': 'V2 raw-raster gate remains failed. This V3 recovery restores the archived sensor sample. Original controller snapshots were not saved; full archived action/RNG history is checked against every physical state and feedback, and controller traces are compared across two reconstructions. No new policy decision or outcome is produced.'}
        (output / 'REPORT.json').write_text(json.dumps(report, indent=2, sort_keys=True))
        passed = True
        if keep_environment:
            return env, obs, selection, history, report
        env.close()
        closed = True
        return None, None, None, history, report
    finally:
        if not closed and (not keep_environment or not passed):
            env.close()
