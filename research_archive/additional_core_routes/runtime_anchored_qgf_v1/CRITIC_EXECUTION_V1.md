# Runtime-Anchored Critic Execution V1

Twelve fixed physical groups are assigned to three group-disjoint folds. Three
fixed seeds train matched action-aware, state-only, and within-bank permutation
models for exactly 3,000 updates. The action representation is initialized from
the outcome-blind, independently audited masked-action encoder of the matching
seed and frozen before labels are read. All nine workers must complete. Every
seed must beat both controls, show at least 90% action sensitivity, and both
physical-group bootstrap improvement lower bounds must exceed zero. Passing is
critic qualification only, not online QGF efficacy.
