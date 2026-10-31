# New Training-Behavior Route, Not an Extension of the Stopped60

User authorized redetermining the route after frozen60 ended56S4F. Do not lower
the six-failure gate, repeatedly sample N1 until failures appear, use old formal
failures for training, or edit the original60. No real v2 critic exists yet.

Hypothesis: a high-success N1 behavior policy lacks useful failure/action support.
Collect real training-only trajectories by uniformly selecting among4 finite,
non-identical native WAM proposals at the SAME observation and replan boundary.
Use seed offsets0/1/2/3 with the frozen checkpoint/denoise10/execute10/action16D.
No added actuator noise, shortened deadlines, changed simulator success predicate,
synthetic failure labels, reward-based selection or full-episode oracle.

This is off-policy exploration data, NOT baseline evaluation, QGF gains or an
assertion that random selection will produce failures. MC returns describe the
behavior continuation and are not counterfactual optimal/base-policy Q targets.
Any later mixed-behavior training must disclose source composition and test on
the unmodified official baseline with independent validation/formal seeds.

## Only admitted launch now: one safety/timing episode

Task stack_bowls_three/demo_randomized, exact scene202619000, no feasibility-seed
replacement, selection RNG202619001; excluded from all future train/val/formal.
Fresh candidate server18341, native baseline reference18231 on dynamically
discovered nodes. Two Slurm tasks, each one distinct assigned GPU: candidate
server and simulator. Entire stage cap45minutes:1.5GPU-hours for those two tasks,
or conservative2.25GPU-hours including the already-loaded native reference GPU.
The reference is queried only for the first-observation parity check. Forecast
15-35minutes based on roughly5 model forwards/replan versus native N1; measure
actual timing rather than launching a larger unbudgeted stage.

Verify candidate0 at first observation against isolated unchanged native server.
For every replan, compare selected proposal with recomputed committed action
(absolute tolerance1e-6), preserving server transaction/memory semantics. Abort
on nonfinite/identical candidates or parity mismatch. Record all candidates,
selected index, diversity, commit error, latency and full R+1 transition audit.
Infrastructure errors remain errors, not failures. Retain all evidence.

After valid smoke, inspect measured cost and state/action coverage. Before any
bulk run freeze a NEW bounded dataset, seed windows, source mixture and split.
Do not automatically launch40/60/100 episodes or train from this engineering
episode. If all candidates are effectively equivalent, stop this route rather
than generate expensive uninformative data. No further original60 collection.
