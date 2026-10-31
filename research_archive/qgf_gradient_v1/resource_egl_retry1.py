"""Correct cleanup for installed MuJoCo2.3.7; no model or benchmark changes."""

import json
import os
from pathlib import Path
import time

import mujoco
import numpy as np
import torch


started = time.monotonic()
assert torch.cuda.device_count() == 1
assert torch.isfinite(torch.ones(16, device='cuda').sum()).item()
model = mujoco.MjModel.from_xml_string('<mujoco><worldbody><geom type="sphere" size=".1"/></worldbody></mujoco>')
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)
renderer = mujoco.Renderer(model, height=32, width=32)
try:
    renderer.update_scene(data)
    pixels = renderer.render()
    assert pixels.shape == (32, 32, 3) and np.isfinite(pixels).all()
finally:
    # This installed release predates Renderer.close(). Release GL while EGL
    # is still initialized instead of relying on interpreter teardown order.
    renderer._mjr_context.free()
    renderer._gl_context.free()
report = dict(status='EGL_RESOURCE_PASS', robot_actions=0, cohort_episodes=0,
              mujoco=mujoco.__version__, shape=list(pixels.shape),
              visible=os.environ['CUDA_VISIBLE_DEVICES'], pid=os.getpid(),
              seconds=time.monotonic() - started)
(Path(os.environ['QGF_RUN']) / 'egl_report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report), flush=True)
