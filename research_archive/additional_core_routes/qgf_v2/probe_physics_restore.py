"""Bounded CPU physics restoration smoke, without robot/model parity claims."""
import json
from pathlib import Path
import sys
import numpy as np
import sapien


physics = sapien.physx.PhysxCpuSystem()
scene = sapien.Scene([physics])
scene.set_timestep(1 / 250)
builder = scene.create_actor_builder()
builder.add_box_collision(half_size=[.02, .02, .02])
actor = builder.build(name='qgf_restore_probe')
actor.set_pose(sapien.Pose([0, 0, 1]))
for _ in range(10):
    scene.step()
packed_physics = physics.pack()
packed_poses = scene.pack_poses()


def trajectory():
    rows = []
    for _ in range(20):
        scene.step()
        pose = actor.get_pose()
        rows.append(np.concatenate([pose.p, pose.q]))
    return np.asarray(rows)


reference = trajectory()
physics.unpack(packed_physics)
scene.unpack_poses(packed_poses)
replay = trajectory()
error = float(np.max(np.abs(reference - replay)))
report = {'scope': 'one free-falling rigid body, CPU physics, 20-step replay',
          'max_pose_error': error, 'finite': bool(np.isfinite(replay).all()),
          'passed': bool(np.isfinite(replay).all() and error <= 1e-7),
          'robot_task_renderer_rng_model_parity': 'not_tested'}
output = Path(sys.argv[1])
if output.exists():
    raise FileExistsError(output)
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
if not report['passed']:
    raise SystemExit(1)
