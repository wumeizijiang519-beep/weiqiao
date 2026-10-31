# Causal Signal V2: Native N8 Full-Chunk Diagnostic

## Motivation

The frozen V1 paired diagnostic completed all 16 groups. A read-only audit
found native action and MuJoCo-state divergence in every group, but no
registered feedback divergence over 10 executed steps. V2 prospectively tests
whether native candidate coverage and intervention horizon caused that failure.

## Fixed population and model

- Reuse exactly the same 16 physical groups, environment seeds, initial states,
  30 dummy waits, archived 100-action prefixes, task order, Simple-WAM weights,
  observation contract, and official success predicate.
- No replacement group, result-dependent task selection, or old branch reuse.
- Candidate seeds are fixed as
  `[10000,11000,12000,13000,14000,15000,16000,17000]`.
- Candidate0 and all seven additional native candidates are generated once
  from the same frozen boundary policy input. Candidate0 replay must be within
  `1e-6`; all eight hashes must be unique and finite with valid gripper values.

## Real interventions

Each candidate is independently executed from a freshly reconstructed exact
physical boundary. The complete native 32-step chunk is open-loop; the WAM is
not called in a branch and outcomes never select a candidate. Save exact
measurements at steps16 and32, or at an earlier official terminal/success.
Action commit error must be at most `1e-6`. All rewards, terminals, successes,
MuJoCo states, observations, videos, and official BDDL goal fractions are
preserved.

## Admission

At least12/16 groups must complete all eight branches. A horizon passes the
binary signal gate only when at least four physical groups across at least two
task families have discordant official success among candidates. A horizon may
authorize only paired-critic research when at least two families have a fixed
10,000-draw physical-group bootstrap 95% lower bound above zero for the range
of final BDDL goal fraction. Bootstrap seed is `202641101`.

V2 is `CAUSAL_SIGNAL_ADMIT` if either step16 or step32 passes one of these
predeclared gates. Otherwise freeze `NO_EXTENDED_NATIVE_ACTION_VALUE_SIGNAL`.
A pass is not online QGF benefit. No critic may be fit from partial groups.

## Staging and budget

Run CPU tests and source/hash registration first. Execute one non-repeating
fixed first-group pilot; only a clean eight-branch pilot can release the other
15 groups. Total V2 cost, including failures, is capped at 4 GPU hours. There
is no automatic retry after a scientific or contract failure.
