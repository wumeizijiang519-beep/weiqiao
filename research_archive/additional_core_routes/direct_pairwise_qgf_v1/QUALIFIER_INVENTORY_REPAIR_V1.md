# Direct-Pairwise Qualifier Inventory Repair V1

The first qualification implementation used an incorrect hard-coded identity
for the single development group with no non-tie pair. It therefore stopped
before reading model metrics. This repair computes the informative-group
inventory directly from the frozen audited corpus and the unchanged `1e-6`
tie rule. It changes no prediction, label, model, control, seed, threshold, or
bootstrap rule. The invalid first output remains preserved and the repaired
qualification is written to new directories.
