"""Add complete MC/TD transition records to the unchanged standard rollout."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unitas_robotwin_trajectory_collector import Recorder, _resize_nearest
import unitas_robotwin_gate_client as base


def transition_fields(starts, final_steps, horizon, success, task_limit):
    starts = np.asarray(starts, dtype=np.int32)
    if not len(starts) or starts[0] != 0:
        raise ValueError('rollout must start at task step zero')
    lengths = np.diff(np.append(starts, int(final_steps))).astype(np.int32)
    if (lengths < 1).any() or (lengths > horizon).any():
        raise ValueError('invalid actual executed chunk lengths')
    if not success and final_steps < task_limit:
        raise ValueError('interrupted rollout is not a negative training episode')
    rewards = np.zeros((len(starts), horizon), dtype=np.float32)
    if success:
        rewards[-1, lengths[-1] - 1] = 1.
    terminal = np.zeros(len(starts), dtype=bool)
    terminal[-1] = True
    return {'executed_steps': lengths, 'rewards': rewards,
            'finite_horizon_terminal': terminal,
            'task_limit': np.asarray(task_limit, dtype=np.int32),
            'task_deadline_reached': np.asarray(not success and final_steps >= task_limit)}


class TransitionRecorder(Recorder):
    def rollout(self, env, *args, **kwargs):
        index = self.index
        seed = getattr(env, '_qgf_checked_seed', None)
        if seed is None:
            raise ValueError('missing independently recorded feasibility seed')
        success = super().rollout(env, *args, **kwargs)
        path = self.output / f'trajectory_{index:03d}.npz'
        with np.load(path, allow_pickle=False) as loaded:
            data = {key: loaded[key] for key in loaded.files}
        final = base.model_observation(env, base._augment_observation(env, env.get_obs()))
        for key, name in (('head_rgb', 'head_camera'), ('left_rgb', 'left_camera'),
                          ('right_rgb', 'right_camera')):
            data[key] = np.concatenate([data[key], _resize_nearest(final['observation'][name]['rgb'])[None]])
        data['joint_positions'] = np.concatenate([
            data['joint_positions'], np.asarray(final['robot_state']['joint_positions'], np.float32)[None]])
        tcp = np.concatenate([final['endpose']['left_tcp_pose'], final['endpose']['right_tcp_pose']])
        data['tcp_pose'] = np.concatenate([data['tcp_pose'], tcp.astype(np.float32)[None]])
        data.update(transition_fields(data['replan_steps'], int(data['final_steps']),
                                      data['action_chunks'].shape[1], success, int(env.step_lim)))
        data['seed'] = np.asarray(seed, dtype=np.int64)
        if any(not np.isfinite(value).all() for value in data.values()
               if np.issubdtype(value.dtype, np.number)):
            raise FloatingPointError('nonfinite transition archive')
        temporary = path.with_suffix('.tmp.npz')
        np.savez_compressed(temporary, **data)
        temporary.replace(path)
        metadata_path = path.with_suffix('.json')
        metadata = json.loads(metadata_path.read_text())
        metadata.update(schema='unitas_transitions_v2', seed=seed,
                        observations=len(data['joint_positions']),
                        actual_executed_steps=data['executed_steps'].tolist(),
                        task_limit=int(env.step_lim), image_shape=list(data['head_rgb'].shape))
        metadata_path.write_text(json.dumps(metadata, indent=2) + '\n')
        return success


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--trajectory-dir', type=Path, required=True)
    parser.add_argument('--candidate-seed-stop', type=int)
    known, remaining = parser.parse_known_args()
    original = base._expert_valid
    known.trajectory_dir.mkdir(parents=True, exist_ok=True)
    def checked(env, setup, episode, seed):
        if known.candidate_seed_stop is not None and seed >= known.candidate_seed_stop:
            raise SystemExit('preregistered disjoint candidate-seed window exhausted')
        try:
            valid, info = original(env, setup, episode, seed)
            record = {'episode': episode, 'seed': int(seed), 'valid': bool(valid)}
        except Exception as exc:
            record = {'episode': episode, 'seed': int(seed), 'error': repr(exc)}
            with (known.trajectory_dir / 'feasibility_attempts.jsonl').open('a') as stream:
                stream.write(json.dumps(record) + '\n')
            raise
        with (known.trajectory_dir / 'feasibility_attempts.jsonl').open('a') as stream:
            stream.write(json.dumps(record) + '\n')
        if valid:
            env._qgf_checked_seed = int(seed)
        return valid, info
    base._expert_valid = checked
    base._rollout = TransitionRecorder(known.trajectory_dir.resolve()).rollout
    sys.argv = [sys.argv[0], *remaining]
    base.main()


if __name__ == '__main__':
    main()
