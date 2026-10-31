# Approved Bounded Extension

The user explicitly approved at most20 additional accepted episodes after the
fixed40 stopped at36success/4failure. This is a disclosed outcome-informed
development-data expansion, not independent evaluation evidence. Retain all40
original episodes and all20 new outcomes. Never alter official success, policy,
checkpoint, action execution or feasibility criteria. No further expansion.

Two parallel ten-episode shards use candidate windows [202616100,202616200)
and [202616200,202616300). Cap each at180minutes, total12GPU-hours; planning
110minutes wall and7.34GPU-hours including two policy servers/two simulators.
If combined60 has fewer than6success or6failure, stop again without training.
Otherwise freeze split seed202616500:48train/12validation, stratified with
at least4training failures and2validation failures, both classes in each.
Original40 has no frozen split or trained critic, so no prior split is replaced.

Use prepare_dataset.py and watch_standard40.py with --extension20-approved.
Separate handoff60 locks, audit, state and logs preserve original40 stop evidence.
After admission launch only the preregistered10000-step TDgamma0.99seed0 pilot
with3600second/oneGPU-hour cap. Budget remaining11 runs from measured timing
before launching them. Same-state branch labels remain disabled.

Deploy no oracle. Train/validation/formal seeds remain isolated; this development
dataset and its losses cannot be reported as online QGF success improvements.
