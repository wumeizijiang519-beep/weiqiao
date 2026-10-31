"""Read-only replay diagnosis; never qualifies recovery or creates policy data."""

import json
import os
from pathlib import Path
import sys
import traceback

import numpy as np
from PIL import Image

from replay_prefix import replay_prefix


RUN = Path(os.environ['QGF_RENDER_DIAGNOSTIC_RUN'])


def difference(a, b):
    delta = np.abs(a.astype(np.float64) - b.astype(np.float64))
    return {'equal': bool(np.array_equal(a, b)), 'changed_values': int(np.count_nonzero(delta)),
            'max_abs': float(delta.max()), 'mean_abs': float(delta.mean())}


def model_image(raw):
    # Matches the official square-camera resize and 180-degree orientation.
    return np.asarray(Image.fromarray(np.ascontiguousarray(raw[::-1, ::-1])).resize(
        (224, 224), resample=Image.Resampling.BILINEAR))


def trace(frame, event, arg):
    if frame.f_code.co_name != 'check_observation':
        return None
    if (event == 'exception' and frame.f_code.co_name == 'check_observation'
            and isinstance(arg[1], RuntimeError)
            and 'Exact archived observation mismatch' in str(arg[1])):
        sys.settrace(None)
        local = frame.f_locals
        env = frame.f_back.f_locals['env']
        actual, expected = local['actual'], local['expected']
        report = {'status': 'DIAGNOSTIC_ONLY_NOT_RECOVERY_PASS', 'boundary': local['index'],
                  'policy_decisions': 0, 'fields': {}, 'repeat_renders': []}
        arrays = {}
        for key in actual:
            report['fields'][key] = difference(actual[key], expected[key])
            if actual[key].ndim == 3:
                a, e = model_image(actual[key]), model_image(expected[key])
                report['fields'][key]['official_resized_uint8'] = difference(a, e)
                arrays['resized_actual_' + key] = a
                arrays['resized_expected_' + key] = e
        camera_key = 'agentview_image'
        for index in range(6):
            rendered = env.sim.render(width=256, height=256, camera_name='agentview', depth=False)
            arrays['render_' + str(index)] = rendered
            report['repeat_renders'].append({
                'raw': difference(rendered, actual[camera_key]),
                'vertical_flip': difference(rendered[::-1], actual[camera_key]),
                'expected_raw': difference(rendered, expected[camera_key]),
                'expected_vertical_flip': difference(rendered[::-1], expected[camera_key])})
        for name in ('geom_xpos', 'geom_xmat', 'cam_xpos', 'cam_xmat', 'light_xpos', 'light_xdir'):
            if hasattr(env.sim.data, name):
                arrays['derived_' + name] = np.asarray(getattr(env.sim.data, name)).copy()
        np.savez_compressed(RUN / 'render_diagnostic.npz', **arrays)
        (RUN / 'DIAGNOSTIC_REPORT.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2), flush=True)
    return trace


if __name__ == '__main__':
    RUN.mkdir(exist_ok=False)
    sys.settrace(trace)
    try:
        replay_prefix(RUN / 'replay')
        (RUN / 'UNEXPECTED_EXACT_REPLAY.json').write_text(json.dumps({'diagnostic_only': True}))
    except Exception:
        (RUN / 'REPLAY_EXCEPTION.txt').write_text(traceback.format_exc())
        if not (RUN / 'DIAGNOSTIC_REPORT.json').exists():
            raise
    finally:
        sys.settrace(None)
