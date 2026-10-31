"""MuJoCo integration-state adapter; no robot/render/WAM coverage claim."""
import numpy as np
import mujoco


class NativeState:
    def __init__(self, model, data):
        self.model = model
        self.data = data
        self.mask = mujoco.mjtState.mjSTATE_INTEGRATION
        self.state = self.current()

    def current(self):
        vector = np.empty(mujoco.mj_stateSize(self.model, self.mask), dtype=np.float64)
        mujoco.mj_getState(self.model, self.data, vector, self.mask)
        return vector

    def restore(self):
        mujoco.mj_setState(self.model, self.data, self.state, self.mask)
        mujoco.mj_forward(self.model, self.data)
        # Forward recomputes derived arrays, and may update integration inputs.
        # Reinstate the saved integration vector before the next physics step.
        mujoco.mj_setState(self.model, self.data, self.state, self.mask)
        if not np.array_equal(self.current(), self.state):
            raise RuntimeError('MuJoCo integration state did not restore exactly')


def cpu_test():
    model = mujoco.MjModel.from_xml_string('''<mujoco><option timestep="0.002"/>
    <size nuserdata="2"/><worldbody><geom type="plane" size="1 1 .1"/>
    <body pos="0 0 .05"><joint name="j" type="slide" axis="0 0 1"/>
    <geom type="sphere" size=".06" mass="1"/></body></worldbody>
    <actuator><motor joint="j"/></actuator></mujoco>''')
    data = mujoco.MjData(model)
    for _ in range(11):
        mujoco.mj_step(model, data)
    data.userdata[:] = [3, 4]
    data.qfrc_applied[:] = .13
    snapshot = NativeState(model, data)

    def trace(sign):
        rows = []
        for step in range(100):
            data.ctrl[:] = sign * np.sin(step * .1)
            mujoco.mj_step(model, data)
            rows.append(snapshot.current())
        return np.stack(rows)

    a = trace(1)
    snapshot.restore()
    b = trace(-1)
    snapshot.restore()
    a1 = trace(1)
    snapshot.restore()
    a2 = trace(1)
    if not np.array_equal(a, a1) or not np.array_equal(a, a2):
        raise RuntimeError('Synthetic native A-B-A state replay differs')
    if np.array_equal(a, b):
        raise RuntimeError('Synthetic perturbation did not exercise native state')
    return {'status': 'SYNTHETIC_NATIVE_CPU_TEST_PASS', 'mujoco_version': mujoco.__version__,
            'mask': int(snapshot.mask), 'vector_size': len(snapshot.state),
            'repeat_max_abs_error': float(np.max(np.abs(a - a1))),
            'actions': 0, 'robot_actions': 0, 'synthetic_physics_steps': 411,
            'wam_restore_gate_passed': False, 'rendering_tested': False}
