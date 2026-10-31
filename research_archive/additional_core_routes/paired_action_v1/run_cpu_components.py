"""Register/check exact component sources, test without GPU or robot episodes."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unittest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    code = Path(__file__).parent
    output = code / 'cpu_components_v1'
    output.mkdir(exist_ok=False)
    sources = {name: sha(code / name) for name in
               ('state_graph.py', 'test_state_graph.py', 'native_state.py', 'run_cpu_components.py')}
    (output / 'SOURCE_REGISTRATION.json').write_text(json.dumps(
        {'sources': sources, 'gpu_work': False, 'robot_actions': 0,
         'tests_not_equivalent_to_complete_robot_snapshot_gate': True}, indent=2))
    try:
        suite = unittest.defaultTestLoader.discover(str(code), pattern='test_state_graph.py')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if not result.wasSuccessful():
            raise RuntimeError('State graph component tests failed')
        from native_state import cpu_test
        report = cpu_test()
        report['graph_unit_tests'] = result.testsRun
        report['sources'] = sources
        if any(sha(code / n) != s for n, s in sources.items()):
            raise RuntimeError('Component source changed during test')
        (output / 'REPORT.json').write_text(json.dumps(report, indent=2, sort_keys=True))
        (output / 'CPU_COMPONENTS_COMPLETE').touch()
        print(json.dumps(report), flush=True)
    except BaseException:
        (output / 'FAILED.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
