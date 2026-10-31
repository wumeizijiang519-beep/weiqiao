# Runtime Inventory Repair V1

Slurm step `1593640.396` failed after 114 GPU seconds while inventorying the
first initialized environment. It made zero WAM calls and executed zero dummy
or robot actions. The failure was an API spelling error in the read-only name
enumerator: MuJoCo exposes joint count as `njnt`, not `njoint`.

The proposed repair changes only the explicit object-kind to count-field map:
`body -> nbody`, `site -> nsite`, `joint -> njnt`, and `geom -> ngeom`. Unknown
kinds now fail closed. It does not change the frozen cohort, support basis,
environment, initial state, progress contract, budget, or scientific gate.

The failed source, log, Slurm state, exit code, and 114 GPU seconds must remain
preserved. Because the original registration forbids automatic GPU retry, this
repair may run only after explicit user approval for one bounded retry. The
retry retains the 300 GPU-second hard cap and has no further automatic retry.
