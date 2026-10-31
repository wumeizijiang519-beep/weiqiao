# QGF v4 Randomized-Intervention Protocol

## Motivation

Both the RGB-statistic v2 critic and the UNITAS-latent v3 critic beat the
same-target state-only control in only one of three fixed bootstrap seeds. The
retained N1 trajectories therefore do not identify same-state action value.
This revision changes the training behavior, not the labels: at each replan it
uniformly commits one of four native stochastic UNITAS proposals generated from
the same current observation. Only the executed proposal receives its observed
finite-horizon return. No unexecuted candidate is assigned a synthetic label.

## Pilot

- Task: `open_microwave/demo_randomized`, selected before this pilot because the
  prior outcome-blind ten-episode gate was 8 success / 2 failure.
- Four new training-only episodes, two independent shards with candidate windows
  `[202622100,202622120)` and `[202622200,202622220)`.
- Uniform selection RNG seeds `202622501` and `202622502`.
- Fixed UNITAS checkpoint, denoise10, execute10, action16D and official success
  predicate. The previously passed fresh-runtime N4/candidate0 parity smoke is
  the engineering prerequisite; no old service is queried or mixed.
- Four allocated A800s form two isolated server/simulator pairs. Hard wall cap is
  two hours and cost cap eight GPU-hours. Every attempted/accepted scene and all
  outcomes are retained.

Pilot admission requires all four transition audits, finite non-identical N4 at
every replan, exact selected-action commit, and at least one success plus one
failure. Failure stops this task/config rather than selecting seeds post hoc.
Passing only authorizes a separately frozen bounded training collection and does
not establish QGF efficacy.

## Decisive evidence

Train on executed randomized actions with episode-disjoint splits and compare
action-aware against the same-target state-only critic. A candidate selector is
frozen only after OOF action evidence. The first efficacy result must then be a
fresh matched online comparison of candidate0 N4, random N4 and QGF N4, reporting
success, rescues, regressions, Wilson interval, McNemar, switching, latency and
compute. No validation/formal seed is reused for training.
