"""Bounded infrastructure qualification; no robot or cohort episodes."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['kernel', 'egl', 'compare'])
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    report = {'mode': args.mode, 'robot_actions': 0, 'cohort_episodes': 0}
    if args.mode == 'compare':
        root = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
        with np.load(args.run / 'arrays.npz', allow_pickle=False) as actual:
            with np.load(root / 'qgf_gradient_v1/STAGE0_ARRAYS.npz', allow_pickle=False) as expected:
                if set(actual.files) != set(expected.files):
                    raise RuntimeError('Resource parity array inventory differs')
                errors = {}
                for key in expected.files:
                    a, b = actual[key], expected[key]
                    if a.shape != b.shape or not np.isfinite(a).all():
                        raise RuntimeError('Resource parity shape/finite mismatch: ' + key)
                    errors[key] = float(np.max(np.abs(a - b)))
                if max(errors.values()) > 1e-6:
                    raise RuntimeError('Resource parity exceeds frozen tolerance: ' + str(errors))
        report['errors'] = errors
    else:
        if torch.cuda.device_count() != 1:
            raise RuntimeError('Worker must expose exactly one assigned GPU')
        a = torch.arange(4096, dtype=torch.float32, device='cuda').reshape(64, 64) / 4096
        value = (a @ a.T).cpu().numpy()
        if not np.isfinite(value).all():
            raise RuntimeError('CUDA kernel produced nonfinite values')
        torch.cuda.synchronize()
        report.update(torch=torch.__version__, gpu=torch.cuda.get_device_name(0),
                      visible=os.environ['CUDA_VISIBLE_DEVICES'])
        if args.mode == 'egl':
            import mujoco
            model = mujoco.MjModel.from_xml_string('<mujoco><worldbody><geom type="sphere" size=".1"/></worldbody></mujoco>')
            data = mujoco.MjData(model)
            mujoco.mj_forward(model, data)
            renderer = mujoco.Renderer(model, height=32, width=32)
            try:
                renderer.update_scene(data)
                pixels = renderer.render()
                if pixels.shape != (32, 32, 3) or not np.isfinite(pixels).all():
                    raise RuntimeError('EGL image contract failed')
                report['render_shape'] = list(pixels.shape)
            finally:
                renderer.close()
    report.update(status='RESOURCE_CHECK_PASS', seconds=time.monotonic() - started,
                  cgroup=Path('/proc/self/cgroup').read_text(), pid=os.getpid())
    (args.run / (args.mode + '_report.json')).write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
