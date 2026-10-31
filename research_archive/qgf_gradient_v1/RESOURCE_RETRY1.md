# Resource cleanup infrastructure repair

Original gpu4 probe rendered its empty32x32 MuJoCo image but failed in our
resource-check finally block: MuJoCo2.3.7 Renderer has no close() method.
Preserve failed55GPU seconds and original sources. No WAM was loaded and no
robot actions/cohort episodes were executed. Do not label original attempt PASS.

One bounded resource retry uses the installed MjrContext.free()/GLContext.free()
before interpreter teardown. This only repairs probe cleanup, not the simulator,
model, actions, cohort, seeds, masks, reward or scientific thresholds. Original
zero_action_probe.py/core.py remain byte-identical. Same fixed frozen Stage0
array comparison1e-6; one GPU3 on owned job1581551 step_extern, max1200seconds.
No automatic further retry. Source SHA list must be saved before launch.

gpu22 checks completed cleanly GPU0=7s/GPU1=3s. Resource cost65GPU seconds
before this retry. Existing Stage01058s plus resource worst1265s=2323s,
within integration2GPUh and20percent reserve. All attempts remain itemized;
separate worker elapsed GPUh from parent allocation reservation GPUh.
