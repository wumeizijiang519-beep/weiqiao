"""Run registered adapter tests without a robot environment or GPU."""
import hashlib
import json
from pathlib import Path
import traceback
import unittest


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    code = Path(__file__).parent
    run = code / 'adapter_cpu_v2'
    run.mkdir(exist_ok=False)
    source_names = ('state_graph.py', 'rng_state.py', 'native_state.py',
                    'external_state.py', 'checkpoint.py', 'build_runtime_schema_plan.py',
                    'test_state_graph.py', 'test_rng_state.py', 'test_external_state.py',
                    'test_checkpoint.py', 'test_runtime_schema_plan.py', Path(__file__).name)
    sources = {name: sha(code / name) for name in source_names}
    (run / 'SOURCE_REGISTRATION.json').write_text(json.dumps(sources, indent=2, sort_keys=True))
    try:
        suite = unittest.defaultTestLoader.discover(str(code), pattern='test_*.py')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if not result.wasSuccessful():
            raise RuntimeError('Adapter unit tests failed')
        import mujoco
        from external_state import ExternalStateError, MjModelState
        from native_state import cpu_test
        native = cpu_test()
        model = mujoco.MjModel.from_xml_string('<mujoco><worldbody><body><geom size=".1"/></body></worldbody></mujoco>')
        static = MjModelState(model, mujoco)
        static.verify()
        original = model.opt.timestep
        model.opt.timestep = original * 2
        mutation_detected = False
        try:
            static.verify()
        except ExternalStateError:
            mutation_detected = True
        finally:
            model.opt.timestep = original
        static.verify()
        if not mutation_detected:
            raise RuntimeError('MjModel binary hash did not detect mutation')
        if any(sha(code / name) != digest for name, digest in sources.items()):
            raise RuntimeError('Registered source changed during tests')
        report = {'status': 'ADAPTER_CPU_V2_PASS_DYNAMIC_ROBOT_GATE_NOT_RUN',
                  'unit_tests': result.testsRun, 'native': native,
                  'mjmodel_mjb_mutation_detected': mutation_detected,
                  'gpu_work': False, 'robot_actions': 0, 'wam_loaded': False,
                  'real_renderer_tested': False, 'sources': sources}
        (run / 'REPORT.json').write_text(json.dumps(report, indent=2, sort_keys=True))
        (run / 'ADAPTER_CPU_V2_PASS').touch()
        print(json.dumps(report, sort_keys=True), flush=True)
    except BaseException:
        (run / 'FAILED.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
