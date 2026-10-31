"""Read-only execution of the installed controller's isolated format_action."""

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from wam_runtime import ROOT, file_sha


def main():
    path = ROOT / 'runtime/simplewam_inference_py310_v2/lib/python3.10/site-packages/robosuite/models/grippers/panda_gripper.py'
    module = ast.parse(path.read_text())
    cls = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == 'PandaGripper')
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'format_action')
    isolated = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
    scope = {'np': np}
    exec(compile(isolated, str(path), 'exec'), scope)
    before = np.asarray([-.4, .4])
    fake = SimpleNamespace(dof=1, current_action=before.copy(), speed=.01)
    after = scope['format_action'](fake, np.asarray([0.]))
    if not np.array_equal(before, after):
        raise RuntimeError('Installed controller does not treat0as neutral')
    dataset_values = np.asarray([0., .5, 1.], dtype=np.float32)
    native = np.sign(-(dataset_values * 2 - 1))
    result = {
        'status': 'READ_ONLY_CONTROLLER_NEUTRAL_ZERO_CONFIRMED',
        'installed_source': str(path), 'source_sha256': file_sha(path),
        'isolated_function': 'PandaGripper.format_action',
        'neutral_input': 0., 'target_before': before.tolist(), 'target_after': after.tolist(),
        'official_postprocessing_expression': 'np.sign(-(2*dataset_gripper-1))',
        'synthetic_dataset_grippers': dataset_values.tolist(), 'native_values': native.tolist(),
        'model_or_environment_loaded': False,
        'scope': 'Controller source semantics only; failed model bank still requires separate replay.'}
    output = ROOT / 'qgf_gradient_v1/gripper_failure_v1/CONTROLLER_SEMANTICS.json'
    if output.exists():
        raise RuntimeError('Never overwrite source diagnostic evidence')
    output.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
