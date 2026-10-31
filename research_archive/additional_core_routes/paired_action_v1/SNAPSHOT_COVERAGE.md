# Required dynamic snapshot coverage, source audit345

Static inventory completed345COMPLETED0:0/6s, zeroGPU,51sourcefiles.
Registration selected16distinct training physical groups, order-invariant CPU
test passed. This does not admit any robot action or prove state restoration.

The official ControlEnv.get_sim_state returns sim.get_state().flatten only.
It does not by itself capture the following visible Python state:

- Environment cur_time,timestep,done,_obs_cache,_observables.
- Observable _current_delay,_current_observed_value,_sampled,
  _time_since_last_sample and filter/corrupter/delayer state.
- Controller goal_pos,goal_ori,ori_ref,relative_ori,kp,kd,new_update,
  initial references,interpolator_pos and interpolator_ori.
- Robot recent_actions/recent_qpos/recent_torques buffers and gripper state.
- MuJoCo warmstart,controls,applied forces and native integration state.
- Caller and local RNG, policy memory, cached observation and rendering state.

Sensor-noise wrapper step() may consume NumPy RNG (motion blur angle and fog
etc). Restoring physical state without wrapper/observable/RNG is insufficient.
Native simulation and rendering objects must not be blindly deep-copied.

Next implement a fail-closed field-by-field serializer preserving reference
identity and snapshot manifests. Treat callbacks/native handles as explicit
audited references, never silently omit unknown mutable objects. Dynamic audit
must compare live raster output as well as physics/reward/controller/RNG.
Source coverage alone is not complete because runtime and native states remain
to inspect. Unknown fields stop admission, not trigger relaxed tolerances.
