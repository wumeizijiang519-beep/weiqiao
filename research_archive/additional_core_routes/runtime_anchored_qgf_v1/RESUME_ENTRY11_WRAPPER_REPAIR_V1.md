# Entry-11 Resume Wrapper Repair V1

The first resume wrapper created its output directory before calling the frozen
runner. The runner intentionally requires `mkdir(exist_ok=False)`, so step
`1593640.415` failed before model construction, candidate generation, or robot
actions. The original empty output and process receipts are preserved.

The only repair removes the premature `mkdir` and uses new output/process names
ending in `_retry1`. No scientific input, runner, model, seed, action, horizon,
threshold, or budget changes. This action-free failure is charged to the same
14,400-second collection cap. There is no further automatic retry.
