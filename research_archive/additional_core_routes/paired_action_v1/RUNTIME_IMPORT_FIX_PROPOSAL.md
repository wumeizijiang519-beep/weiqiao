# Runtime inventory attempt record

Original step1593640.348 failed1:0/115GPUseconds before environment construction,
rendering, WAM load or robot action. It imported benchmark before libero_utils.

Bounded retry1 step1593640.351 failed1:0/108GPUseconds, also before env
construction/render/WAM/action. An operator patch again left benchmark imported
before libero_utils, so official file-logging hook was too late. This is an
operator patch error, not evidence against state restorability. Failed sources,
directories and logs are preserved.

Local source now restores correct order: import experiments.libero.libero_utils
first, then libero.libero benchmark. User explicitly approved one further retry
after being told the old allowance was exhausted; see RUNTIME_INVENTORY_RETRY2.md.
No WAM/model/dummy/robot action occurred in either failed attempt. GPU engineering
costs use sacct actuals115s and108s, not the earlier116s estimate.

CPU synthetic tests:10 graph tests pass; MuJoCo2.3.7 integration state test
exact A-B-A-A,0 error. This is synthetic only, no robot/render coverage and no
dynamic restoration PASS.
