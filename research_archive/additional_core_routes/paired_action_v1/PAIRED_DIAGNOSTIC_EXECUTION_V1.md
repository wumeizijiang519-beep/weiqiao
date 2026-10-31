# Paired Diagnostic Execution V1

Status: implementation preregistration draft; execution requires frozen source
hashes, a clean Raster Contract V2 CPU admission report, budget registration,
and an idle allocated GPU.

The population is exactly the 16 entries in `REGISTRATION.json`. For each
entry, a fresh environment replays the archived 100-step prefix and generates
the native N4 bank with seeds 10000/11000/12000/13000 from the same returned
policy observation. Four fresh branches independently replay that boundary.
Branch order is ascending SHA256 of
`paired-branch-v1|physical_input_group|candidate_index`.

Each branch executes the selected native candidate prefix for at most 10
steps, then uses only native candidate0 (seed 10000) closed-loop replans of at
most 10 steps until 100 diagnostic steps or official terminal/success. The
WAM, task, action mapping, horizon, replan, and success criterion are unchanged.
Only executed branches receive measured rewards and binary outcomes. Direct
renderer hashes are metadata under Raster Contract V2; policy-returned images,
state, RNG, feedback, and actions remain strict fields.

Every group preserves bank, hashes, RNG receipts, boundary receipts, stepwise
actions/rewards/terminal/success/state/policy-observation hashes, videos, and
errors. A group error marks that fixed group unavailable and never triggers a
replacement. Admission requires at least 12 complete groups and at least four
groups spanning two task families with differing binary branch outcomes. This
is a signal diagnostic, not QGF efficacy and not deployment authorization.
