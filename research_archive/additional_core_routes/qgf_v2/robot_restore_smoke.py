"""Bounded actual-task restore probe; never produces training branch labels."""
import argparse
import copy
import json
import os
from pathlib import Path
import random
import sys
import traceback
import numpy as np
import torch


def run(args):
    root = args.root.resolve()
    sys.path[:0] = [str(root), str(root / 'script'), str(root / 'description/utils'), str(root.parent)]
    os.chdir(root)
    import unitas_robotwin_gate_client as base
    from unitas.inference.client import PolicyClient
    random.seed(202614000)
    np.random.seed(202614000)
    torch.manual_seed(202614000)
    env, setup = base._load_environment('stack_bowls_three', 'demo_randomized')
    attempts = []
    try:
        info = None
        for seed in range(202614000, 202614005):
            try:
                valid, info = base._expert_valid(env, setup, 0, seed)
                attempts.append({'seed': seed, 'valid': valid})
            except Exception as exc:
                attempts.append({'seed': seed, 'error': repr(exc)})
                continue
            if valid:
                break
        else:
            raise RuntimeError('five-scene feasibility cap reached')
        env.setup_demo(now_ep_num=0, seed=seed, is_test=True, **setup)
        instruction = base._episode_instruction('stack_bowls_three', info, 'unseen')
        env.set_instruction(instruction=instruction)
        env.actor_pose = True
        env._policy_native_failed = False
        env._update_render()
        obs = base._augment_observation(env, env.get_obs())
        with PolicyClient(args.host, args.port, domain='robotwin') as client:
            client.reset()
            actions = np.asarray(client.act(base.model_observation(env, obs), instruction, []))[:2].copy()
        if actions.shape != (2, 16) or not np.isfinite(actions).all():
            raise ValueError('need two finite 16D actions')
        physics = env.scene.physx_system
        physical = physics.pack()
        poses = env.scene.pack_poses()
        # This deliberately tests a minimal restore; controller caches are not certified.
        fields = {key: copy.deepcopy(value) for key, value in vars(env).items()
                  if isinstance(value, (bool, int, float, str, type(None), np.ndarray))}
        robot_fields = {key: copy.deepcopy(value) for key, value in vars(env.robot).items()
                        if isinstance(value, (bool, int, float, str, type(None), np.ndarray))}
        joints = []
        seen = set()
        for entity in (env.robot.left_entity, env.robot.right_entity):
            for joint in entity.get_active_joints():
                if id(joint) not in seen:
                    seen.add(id(joint))
                    joints.append((joint, np.asarray(joint.get_drive_target()).copy(),
                                   np.asarray(joint.get_drive_velocity_target()).copy()))
        def joint_state():
            return np.concatenate([np.asarray(entity.get_qpos())
                                   for entity in (env.robot.left_entity, env.robot.right_entity)])
        saved_joints = joint_state().copy()
        rng = (random.getstate(), np.random.get_state(), torch.get_rng_state(),
               torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else None)

        def reset_planners():
            if not args.reset_planners:
                return
            if env.robot.communication_flag:
                for conn in (env.robot.left_conn, env.robot.right_conn):
                    conn.send({'cmd': 'reset'})
                    if conn.recv() != 'ok':
                        raise RuntimeError('planner reset failed')
            else:
                for planner in (env.robot.left_planner, env.robot.right_planner):
                    planner.motion_gen.reset(reset_seed=True)

        plan_trace = []
        originals = {}
        replay_plan_queue = []
        for name in ('left_plan_path', 'right_plan_path'):
            originals[name] = getattr(env.robot, name)
            def traced(*values, _name=name, **kwargs):
                if replay_plan_queue:
                    expected_name, saved = replay_plan_queue.pop(0)
                    if expected_name != _name:
                        raise RuntimeError('planner replay ordering mismatch')
                    result = copy.deepcopy(saved)
                else:
                    result = originals[_name](*values, **kwargs)
                plan_trace.append((_name, copy.deepcopy(result)))
                return result
            setattr(env.robot, name, traced)

        def images_from(payload):
            return np.stack([payload['observation'][name]['rgb']
                             for name in ('head_camera', 'left_camera', 'right_camera')])

        static_images = images_from(base.model_observation(env, obs))
        env._update_render()
        static_repeat = images_from(base.model_observation(env, base._augment_observation(env, env.get_obs())))
        static_rgb_error = int(np.abs(static_images.astype(np.int16) - static_repeat.astype(np.int16)).max())

        def replay():
            states, images = [], []
            for action in actions:
                env.take_action(action, action_type='ee')
                current = base._augment_observation(env, env.get_obs())
                payload = base.model_observation(env, current)
                states.append(payload['robot_state']['joint_positions'])
                images.append(np.stack([payload['observation'][name]['rgb']
                                        for name in ('head_camera', 'left_camera', 'right_camera')]))
            return np.asarray(states), np.asarray(images)

        reset_planners()
        first, first_images = replay()
        reference_plans = list(plan_trace)
        plan_trace.clear()
        physics.unpack(physical)
        env.scene.unpack_poses(poses)
        vars(env).update(copy.deepcopy(fields))
        vars(env.robot).update(copy.deepcopy(robot_fields))
        for joint, target, velocity in joints:
            joint.set_drive_target(target)
            joint.set_drive_velocity_target(velocity)
        immediate_error = float(np.abs(joint_state() - saved_joints).max())
        random.setstate(rng[0])
        np.random.set_state(rng[1])
        torch.set_rng_state(rng[2])
        if rng[3] is not None:
            torch.cuda.set_rng_state_all(rng[3])
        reset_planners()
        env._update_render()
        if args.replay_plans:
            replay_plan_queue.extend(copy.deepcopy(reference_plans))
        second, second_images = replay()
        if replay_plan_queue:
            raise RuntimeError('unconsumed diagnostic planner replay')
        plan_errors = []
        for (name, ref), (other, repeated) in zip(reference_plans, plan_trace):
            if name != other or ref['status'] != repeated['status']:
                plan_errors.append(None)
            elif ref['status'] == 'Success':
                a, b = np.asarray(ref['position']), np.asarray(repeated['position'])
                plan_errors.append(float(np.abs(a - b).max()) if a.shape == b.shape else None)
        error = float(np.max(np.abs(first - second)))
        image_error = int(np.max(np.abs(first_images.astype(np.int16) - second_images.astype(np.int16))))
        np.savez_compressed(args.output.parent / 'replay_evidence.npz',
                            actions=actions, first_states=first, replay_states=second,
                            first_images=first_images, replay_images=second_images)
        return {'scope': 'actual-task controls-aware restore, two fixed actions only',
                'accepted_seed': seed, 'feasibility_attempts': attempts,
                'restored_drive_joints': len(joints),
                'robot_fields_restored': sorted(robot_fields),
                'immediate_joint_restore_error': immediate_error,
                'static_rerender_rgb_max_abs_error': static_rgb_error,
                'planner_reset_mode': bool(args.reset_planners),
                'diagnostic_recorded_plans': bool(args.replay_plans),
                'planner_position_errors': plan_errors,
                'planner_call_counts': [len(reference_plans), len(plan_trace)],
                'joint_max_abs_error': error, 'rgb_max_abs_error': image_error,
                'finite': bool(np.isfinite(first).all() and np.isfinite(second).all()),
                'short_replay_passed': bool(np.isfinite(second).all() and error <= 1e-6 and image_error == 0),
                'full_branch_admission': False,
                'outstanding': 'controller/drive/memory state audit, longer contact-rich replay',
                'training_labels_collected': 0}
    finally:
        env.close_env()


parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--host', required=True)
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--reset-planners', action='store_true')
parser.add_argument('--replay-plans', action='store_true',
                    help='diagnostic only: isolate physics from planner randomness')
args = parser.parse_args()
if args.output.exists():
    raise FileExistsError(args.output)
try:
    report = run(args)
except Exception:
    report = {'status': 'FAILED', 'traceback': traceback.format_exc(), 'full_branch_admission': False}
args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
if report.get('status') == 'FAILED' or not report.get('short_replay_passed', False):
    raise SystemExit(1)
