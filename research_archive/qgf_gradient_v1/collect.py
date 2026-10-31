"""Prospective, manifest-bound randomized native-prefix data collection."""

import argparse
import copy
import json
from pathlib import Path
import random
import shutil
import time
import traceback

import imageio.v2 as imageio
import numpy as np
import torch

from core import GuidanceConfig, GuidedScheduler
from data_contract import (array_hash, capture_rng, normalized_executed_action,
                           native_from_normalized,
                           observation_hash, observation_payload, restore_rng,
                           rng_hash, save_rng, validate_transition)
from wam_runtime import (CHECKPOINT_SHA, MANIFEST_SHA, ROOT, STATS_SHA,
                         file_sha, load_wam)


SEEDS = (10000, 11000, 12000, 13000)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True))


def seed_environment(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def image_frame(obs):
    from experiments.libero.libero_utils import get_libero_image

    images = get_libero_image(obs)
    return np.concatenate([images['image'], images['wrist_image']], axis=1)


def context_hash(cache):
    return {key: array_hash(value.detach().cpu().float().numpy())
            for key, value in cache.items()}


def check_registered_buffers(model):
    return {name: array_hash(value.detach().cpu().float().numpy())
            for name, value in model.named_buffers()}


def run_episode(entry, folder, cfg, model, processor):
    from experiments.libero.eval_libero_single import _predict_action_chunk
    from experiments.libero.libero_utils import (LIBERO_ENV_RESOLUTION,
                                                get_libero_dummy_action, get_libero_env)
    from libero.libero import benchmark

    folder.mkdir(exist_ok=False)
    write_json(folder / 'config.json', entry)
    started = time.perf_counter()
    for key, digest_key in [('initial_state_path', 'initial_file_sha256'),
                            ('bddl_path', 'bddl_sha256')]:
        if file_sha(entry[key]) != entry[digest_key]:
            raise RuntimeError('Frozen scene asset mismatch: ' + key)
    states = np.asarray(torch.load(entry['initial_state_path'], map_location='cpu', weights_only=False))
    if '_add_' in Path(entry['initial_state_path']).name or '_level' in Path(entry['initial_state_path']).name:
        states = states.reshape(1, -1)
    initial = np.asarray(states[entry['initial_state_index']], dtype='<f8')
    import hashlib
    if hashlib.sha256(initial.tobytes()).hexdigest() != entry['state_sha256']:
        raise RuntimeError('Frozen initial state mismatch')
    suite = benchmark.get_benchmark_dict()['libero_10']()
    task = suite.get_task(entry['task_id'])
    if task.name != entry['task_name']:
        raise RuntimeError('Task catalogue order changed')
    seed_environment(entry['environment_seed'])
    env, description = get_libero_env(task, LIBERO_ENV_RESOLUTION, entry['environment_seed'])
    writer = None
    cache = {}
    selection = np.random.default_rng(entry['selection_seed'])
    scheduler = model.infer_action_scheduler
    action_key = processor.shape_meta['action'][0]['key']
    normalizer = processor.normalizer.normalizers['action'][action_key]
    scale = normalizer.scale.detach().cpu().float().numpy()
    offset = normalizer.offset.detach().cpu().float().numpy()
    scale, offset = np.broadcast_to(scale, (7,)).copy(), np.broadcast_to(offset, (7,)).copy()
    selected_counts = [0] * 4
    steps, replan = 0, 0
    previous_next = None
    episode_done, success = False, False
    video_frames = 0
    transition_records = []

    def append_frame(obs):
        nonlocal video_frames
        writer.append_data(image_frame(obs))
        video_frames += 1

    def predict(obs, seed):
        wrapper = GuidedScheduler(scheduler, GuidanceConfig(weight=0, projected=False))
        model.infer_action_scheduler = wrapper
        cfg.seed = seed
        torch.cuda.synchronize()
        start = time.perf_counter()
        try:
            action, *_ = _predict_action_chunk(
                obs, description, model, processor, cfg, action_horizon=32,
                input_h=224, input_w=448, model_device='cuda',
                profile_action_chunk_time=True, prompt_cache=cache)
            torch.cuda.synchronize()
            native = np.asarray(action, dtype=np.float32).copy()
            raw = wrapper.final_sample.numpy()[0].copy()
            if native.shape != (32, 7) or raw.shape != (32, 7):
                raise RuntimeError('Wrong model action shape')
            return native, raw, time.perf_counter() - start
        finally:
            model.infer_action_scheduler = scheduler

    try:
        env.reset()
        obs = env.set_init_state(initial)
        actual_initialized = np.asarray(env.get_sim_state()).copy()
        np.savez_compressed(folder / 'initialization.npz', frozen_input=initial,
                            actual_initialized=actual_initialized)
        if actual_initialized.shape != initial.shape or np.max(np.abs(actual_initialized - initial)) > 1e-6:
            raise RuntimeError('Simulator did not restore the frozen initial state')
        writer = imageio.get_writer(folder / 'rollout.mp4', fps=24)
        append_frame(obs)
        dummy_rewards, dummy_states = [], [actual_initialized]
        for _ in range(30):
            obs, reward, done, _ = env.step(get_libero_dummy_action())
            dummy_rewards.append(float(reward))
            dummy_states.append(np.asarray(env.get_sim_state()).copy())
            append_frame(obs)
            episode_done = bool(done)
            success = bool(env.check_success())
        np.savez_compressed(folder / 'dummy_wait.npz', rewards=np.asarray(dummy_rewards),
                            sim_states=np.stack(dummy_states))
        np.savez_compressed(folder / 'observation_0000.npz', **observation_payload(obs))
        save_rng(folder / 'episode_rng.npz', capture_rng())
        write_json(folder / 'runtime_config.json', {
            'task_description': description, 'action_scale': scale.tolist(), 'action_offset': offset.tolist(),
            'policy_memory': 'Stateless official infer_action; per-call video cache; immutable text context.',
            'horizon': 32, 'replan': 10, 'model_step_limit': 700, 'dummy_wait': 30,
            'initial_state_max_abs_error': float(np.max(np.abs(actual_initialized - initial))),
            'actual_initial_state_hash': array_hash(actual_initialized),
            'preboundary_terminal': bool(episode_done or success),
        })
        while steps < 700 and not episode_done and not success:
            transition_dir = folder / f'transition_{replan:04d}'
            transition_dir.mkdir()
            current = observation_payload(obs)
            current_hash = observation_hash(current)
            before_state = np.asarray(env.get_sim_state()).copy()
            pre_rng = capture_rng()
            save_rng(transition_dir / 'rng_before.npz', pre_rng)
            bank, raw_bank, latencies, post_rngs = [], [], [], []
            for seed in SEEDS:
                restore_rng(pre_rng)
                native, raw, latency = predict(current, seed)
                bank.append(native)
                raw_bank.append(raw)
                latencies.append(latency)
                post_rngs.append(capture_rng())
            bank, raw_bank = np.stack(bank), np.stack(raw_bank)
            post0 = post_rngs[0]
            for i, state in enumerate(post_rngs):
                save_rng(transition_dir / f'rng_candidate_{i}_post.npz', state)
            selected_state_before = copy.deepcopy(selection.bit_generator.state)
            selected = int(selection.integers(0, 4))
            selected_counts[selected] += 1
            immutable_context = context_hash(cache)
            buffers_before_replay = check_registered_buffers(model) if replan == 0 else None
            restore_rng(pre_rng)
            replay, replay_raw, replay_time = predict(current, SEEDS[selected])
            replay_error = float(np.max(np.abs(replay - bank[selected])))
            if replan == 0:
                restore_rng(pre_rng)
                repeat0, _, repeat_time = predict(current, SEEDS[0])
                candidate0_error = float(np.max(np.abs(repeat0 - bank[0])))
                if check_registered_buffers(model) != buffers_before_replay:
                    raise RuntimeError('Registered model buffers changed during replay')
            else:
                candidate0_error, repeat_time = None, None
            if replay_error > 1e-6 or np.max(np.abs(replay_raw - raw_bank[selected])) > 1e-6:
                raise RuntimeError('Selected inference is not reproducible')
            if candidate0_error is not None and candidate0_error > 1e-6:
                raise RuntimeError('Candidate0 replay failed')
            if immutable_context != context_hash(cache):
                raise RuntimeError('Prompt cache changed during replay')
            if not np.array_equal(before_state, np.asarray(env.get_sim_state())):
                raise RuntimeError('Candidate inference changed simulator state')
            if current_hash != observation_hash(observation_payload(obs)):
                raise RuntimeError('Candidate inference changed input observation')
            restore_rng(post0)
            caller_rng = capture_rng()
            save_rng(transition_dir / 'rng_caller_committed.npz', caller_rng)
            write_json(transition_dir / 'selection.json', {
                'before': selected_state_before, 'after': selection.bit_generator.state,
                'selected_index': selected, 'selection_seed': entry['selection_seed'],
                'candidate0_replay_error': candidate0_error, 'selected_replay_error': replay_error,
                'selected_replay_seconds': replay_time, 'candidate0_replay_seconds': repeat_time,
                'prompt_context_hashes': immutable_context,
            })
            normalized = normalized_executed_action(bank, scale, offset)
            # Persist proposals before executing any action, including failed attempts.
            np.savez_compressed(transition_dir / 'proposals.npz', candidates_native=bank,
                                candidates_raw_normalized=raw_bank,
                                candidates_executed_normalized=normalized,
                                selected_index=np.asarray(selected), action_scale=scale, action_offset=offset)
            if (not np.isfinite(bank).all() or not np.isfinite(raw_bank).all()
                    or not np.isfinite(normalized).all()
                    or not np.isin(bank[..., -1], [-1, 1]).all()
                    or len({array_hash(action) for action in bank}) != 4):
                raise RuntimeError('Invalid native bank; no action committed')
            if np.max(np.abs(native_from_normalized(normalized, scale, offset) - bank)) > 1e-6:
                raise RuntimeError('Invalid action mapping; no action committed')
            executed, rewards, dones, successes = [], [], [], []
            sim_states = [before_state]
            remaining_before = 700 - steps
            for action in bank[selected, :min(10, remaining_before)]:
                committed = action.copy()
                obs, reward, done, _ = env.step(committed)
                executed.append(committed.copy())
                rewards.append(float(reward))
                episode_done = bool(done)
                success = bool(env.check_success())
                dones.append(episode_done)
                successes.append(success)
                steps += 1
                sim_states.append(np.asarray(env.get_sim_state()).copy())
                append_frame(obs)
                # A crash retains the exact prefix of real feedback without labels for others.
                np.savez_compressed(transition_dir / 'execution_progress.npz',
                                    executed_actions=np.stack(executed), rewards=np.asarray(rewards),
                                    environment_done=np.asarray(dones), success=np.asarray(successes),
                                    sim_states=np.stack(sim_states))
                if episode_done or success or steps == 700:
                    break
            length = len(executed)
            labels = np.full(4, np.nan, dtype=np.float64)
            labels[selected] = sum(rewards)
            data = dict(candidates_native=bank, candidates_raw_normalized=raw_bank,
                        candidates_executed_normalized=normalized,
                        candidate_seeds=np.asarray(SEEDS),
                        candidate_hashes=np.asarray([array_hash(a) for a in bank]),
                        selected_index=np.asarray(selected), actual_length=np.asarray(length),
                        executed_actions=np.stack(executed), rewards=np.asarray(rewards),
                        step_environment_done=np.asarray(dones), step_success=np.asarray(successes),
                        candidate_returns=labels, environment_done=np.asarray(episode_done),
                        success=np.asarray(success), time_limit=np.asarray(steps == 700),
                        terminal=np.asarray(episode_done or success or steps == 700),
                        remaining_before=np.asarray(remaining_before), remaining_after=np.asarray(700 - steps),
                        caller_rng_hash=np.asarray(rng_hash(caller_rng)),
                        candidate0_post_rng_hash=np.asarray(rng_hash(post0)),
                        selected_replay_error=np.asarray(replay_error),
                        latencies_sec=np.asarray(latencies), action_scale=scale, action_offset=offset,
                        sim_states=np.stack(sim_states),
                        **{'current_' + key: value for key, value in current.items()},
                        **{'next_' + key: value for key, value in observation_payload(obs).items()})
            audit = validate_transition(data, previous_next)
            previous_next = audit.pop('next_obs')
            np.savez_compressed(transition_dir / 'transition.npz', **data)
            np.savez_compressed(folder / f'observation_{replan + 1:04d}.npz', **previous_next)
            save_rng(transition_dir / 'rng_after_execution.npz', capture_rng())
            pairwise = [float(np.abs(bank[i] - bank[j]).mean()) for i in range(4) for j in range(i)]
            transition_records.append({**audit, 'selected': selected, 'length': length,
                                       'path': str(transition_dir.relative_to(folder)),
                                       'pairwise_mad_min': min(pairwise),
                                       'transition_sha256': file_sha(transition_dir / 'transition.npz')})
            if min(pairwise) <= 0:
                raise RuntimeError('Native candidate diversity is zero')
            write_json(folder / 'progress.json', {'model_steps': steps, 'replans': replan + 1,
                                                 'success': success, 'last_transition': transition_records[-1]})
            print(entry['episode_id'], replan, steps, 'success=', success, flush=True)
            replan += 1
        summary = {
            **entry, 'task_description': description, 'success': success,
            'model_steps': steps, 'dummy_steps': 30, 'replans': replan,
            'environment_done': episode_done, 'time_limit': steps == 700,
            'preboundary_terminal': steps == 0, 'selected_counts': selected_counts,
            'video_frames': video_frames, 'audit_pass': True, 'transitions': transition_records,
            'wall_seconds': time.perf_counter() - started,
            'checkpoint_sha256': CHECKPOINT_SHA, 'stats_sha256': STATS_SHA,
        }
    finally:
        model.infer_action_scheduler = scheduler
        if writer is not None:
            writer.close()
        env.close()
    summary['video_sha256'] = file_sha(folder / 'rollout.mp4')
    write_json(folder / 'summary.json', summary)
    (folder / 'EPISODE_COMPLETE').touch()
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_text())
    for name, expected_sha in registration['source_sha256'].items():
        if file_sha(Path(__file__).parent / name) != expected_sha:
            raise RuntimeError('Collector source differs from registration: ' + name)
    manifest_path = ROOT / 'qgf_gradient_v1/evidence/COHORT_MANIFEST.json'
    if file_sha(manifest_path) != MANIFEST_SHA:
        raise RuntimeError('Changed frozen population')
    manifest = json.loads(manifest_path.read_text())
    entries = {row['episode_id']: row for row in manifest['partitions']['train']}
    if len(set(registration['episode_ids'])) != len(registration['episode_ids']):
        raise RuntimeError('Duplicate dispatch entries')
    if args.run.exists():
        raise RuntimeError('Never overwrite a run directory')
    args.run.mkdir()
    (args.run / 'source').mkdir()
    for name in registration['source_sha256']:
        shutil.copy2(Path(__file__).parent / name, args.run / 'source' / name)
    write_json(args.run / 'registration.json', registration)
    start = time.perf_counter()
    try:
        cfg, model, processor = load_wam(args.run)
        summaries = []
        for episode_id in registration['episode_ids']:
            summaries.append(run_episode(entries[episode_id], args.run / episode_id, cfg, model, processor))
        report = {'status': 'COLLECTION_COMPLETE_PENDING_INDEPENDENT_AUDIT',
                  'episodes': summaries, 'wall_seconds': time.perf_counter() - start,
                  'peak_cuda_bytes': torch.cuda.max_memory_allocated(),
                  'manifest_sha256': MANIFEST_SHA, 'registration_sha256': file_sha(args.registration)}
        write_json(args.run / 'report.json', report)
        (args.run / 'COLLECTION_COMPLETE').touch()
    except BaseException:
        (args.run / 'FAILED.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
